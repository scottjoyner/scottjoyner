#!/usr/bin/env python3
"""Validate synthetic RAM/pread/mmap shortlist storage study from raw receipts.

All dataset cases and seeds are fixed. This verifier independently recomputes
latency medians, process RSS and retrieval accuracy for each storage path.
"""
import argparse
import json
import statistics
from pathlib import Path

SOURCE_SHA = "5823f169d9476f5105d41c78a9d77d08a507139240554dd5b1d08f6542f2b1e5"
MODES = ["ram", "pread_warm", "pread_hint", "mmap_warm", "mmap_hint"]
SHORTLISTS = [20, 160]
WORKLOADS = [(8192, "clustered"), (32768, "clustered")]
SEEDS = list(range(20261140, 20261145))
DIM = 768
QUERIES = 12
REPS = 2

def median(rows, key):
    return statistics.median(row[key] for row in rows)

def close(x, y, tol=0.00002):
    return abs(x-y) <= tol

def verify(obj):
    if obj.get("schema_version")!=1 or obj.get("kind")!="synthetic_secondary_float32_rerank_storage_study" or (
            obj.get("source_sha256") != SOURCE_SHA):
        raise ValueError("Invalid artifact provenance")
    if (obj.get("seed_values"),obj.get("modes"),obj.get("shortlist_sizes"),obj.get("dimensions"),
        obj.get("queries"),obj.get("repeats")) != (SEEDS, MODES, SHORTLISTS, DIM, QUERIES, REPS):
        raise ValueError("Unexpected experiment design")
    if obj.get("workloads") != [{"n": n, "distribution": mode} for n, mode in WORKLOADS]:
        raise ValueError("Wrong workload")
    trials=obj.get("raw_trials",[])
    if len(trials) != len(SEEDS)*len(MODES)*len(SHORTLISTS)*len(WORKLOADS):
        raise ValueError("Expected 100 independent-process runs")
    unique={}
    truth={}
    for t in trials:
        n,dist,m,storage,seed = (t["vectors"],t["distribution"],t["shortlist_m"],
                                  t["mode"],t["seed"])
        key=(n,dist,m,storage,seed)
        if key in unique:
            raise ValueError("Duplicate trial")
        unique[key]=t
        if ((n,dist) not in WORKLOADS or storage not in MODES or m not in SHORTLISTS
              or seed not in SEEDS):
            raise ValueError("Unknown workload or seed")
        if ((t.get("status"),t.get("sanity_failures"))!=("PASS",0)
            or (t.get("dimensions"),t.get("queries"),t.get("repeats"),t.get("top_k"))!=(768,12,2,5)):
            raise ValueError("Incorrect or missing sanity validation")
        if t["opportunities"] != 60 or not 0<=t["hits"]<=60 or abs(
                t["recall_at5"]-t["hits"]/60)>1e-7:
            raise ValueError("Incorrect recall values")
        if any(t[key]<=0 for key in ["query_p50_ms","query_p95_ms","scan_p50_ms",
                                    "rerank_fetch_p50_ms","float32_reference_p50_ms",
                                    "rss_after_query_kib"]):
            raise ValueError("Missing timing or process RSS")
        if not t["float32_resident_in_heap"] and storage=="ram":
            raise ValueError("RAM baseline released original")
        if storage=="ram":
            if t["read_calls"] or t["backing_file_size_bytes"]:
                raise ValueError("RAM baseline unexpectedly used file")
        else:
            if t["backing_file_size_bytes"]!=n*DIM*4 or t["float32_resident_in_heap"]:
                raise ValueError("Backing-file size mismatch")
            if storage.startswith("pread"):
                if t["read_calls"] != QUERIES*REPS*m or (
                    t["read_bytes"] != t["read_calls"]*DIM*4):
                    raise ValueError("Pread accounting mismatch")
            elif t["read_calls"]!=0:
                raise ValueError("mmap incorrectly recorded pread")
        if t["hint_failures"] != 0:
            raise ValueError("Hint failed")
        tk=(n,dist,m,seed)
        if tk in truth and truth[tk]!=t["hits"]:
            raise ValueError("Same deterministic data yielded different retrieval correctness")
        truth[tk]=t["hits"]
    recomputed={}
    summary=obj.get("summary",{})
    for n,dist in WORKLOADS:
        label=f"{n}/{dist}"
        for m in SHORTLISTS:
            root=summary[label][str(m)]
            paths={}
            for mode in MODES:
                group=[]
                for seed in SEEDS:
                    key=(n,dist,m,mode,seed)
                    if key not in unique:
                        raise ValueError("Missing specific trial")
                    group.append(unique[key])
                record=root[mode]
                hits=sum(t["hits"] for t in group)
                if (record["top5_hits"],record["top5_opportunities"])!=(hits,300):
                    raise ValueError("Incorrect aggregated hits")
                for key,fn in [
                    ("median_query_p50_ms","query_p50_ms"),
                    ("median_query_p95_ms","query_p95_ms"),
                    ("median_rss_after_query_kib","rss_after_query_kib"),
                    ("median_quantization_ms","quantization_ms"),
                    ("median_backing_file_setup_ms","backing_file_setup_ms")
                ]:
                    if not close(record[key],median(group,fn)):
                        raise ValueError(f"Incorrect {label}/{m}/{mode}/{key}")
                if not close(record["recall_at5"],hits/300):
                    raise ValueError("Recall summary mismatch")
                if record["sum_major_page_faults"] != sum(t["major_faults_delta"] for t in group):
                    raise ValueError("Major page fault totals mismatched")
                paths[mode]={
                    "hits":hits,
                    "recall":round(hits/300,6),
                    "median_query_p50_ms":round(median(group,"query_p50_ms"),6),
                    "median_rss_kib":round(median(group,"rss_after_query_kib"),1),
                }
            rss_ram=paths["ram"]["median_rss_kib"]
            for mode in MODES:
                record=root[mode]
                if not close(record["query_p50_ratio_vs_ram"],
                             paths[mode]["median_query_p50_ms"] / paths["ram"]["median_query_p50_ms"],0.0001):
                    raise ValueError("Inconsistent latency ratio")
                if not close(record["process_rss_fraction_of_ram"],
                             paths[mode]["median_rss_kib"] / rss_ram,0.0001):
                    raise ValueError("Inconsistent process RSS ratio")
            recomputed[f"{label}/M{m}"]=paths
    return {
        "status":"PASS","runs":len(trials),
        "distinct_seed_workload_shortlist_cases":len(truth),
        "storage_paths":MODES,"summary":recomputed,
        "caveat":"File-backed RSS excludes Linux page cache; eviction hints do not guarantee cold reads.",
    }

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("path",nargs="?",type=Path,
        default=Path(__file__).parent/"results"/"2026-10-29-float-storage-study.json")
    args=parser.parse_args()
    print(json.dumps(verify(json.loads(args.path.read_text(encoding="utf-8"))),indent=2))
