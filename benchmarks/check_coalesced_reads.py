#!/usr/bin/env python3
"""Independent auditor of 140 synthetic CPU candidate-read locality experiments.

Reconstructs read byte counts, coalesced run counts, recall parity,
per-seed coverage, latency medians, process memory and ratios from receipts.
"""
import argparse
import json
import statistics
from pathlib import Path

SOURCE = "d2f4ed078d87bff565dcc26e74f67c3967b801311ac08087b27b915159496c4e"
WORKLOADS = [(8192, "temporal"), (8192, "clustered"),
             (32768, "temporal"), (32768, "clustered")]
MODES = ["ram", "pread_rank_warm", "pread_sorted_warm", "pread_coalesced_warm",
         "pread_rank_hint", "pread_sorted_hint", "pread_coalesced_hint"]
MVALS = [20, 160]
SEEDS = list(range(20261150,20261155))
NQ,REPS,D = 12,2,768

def close(a,b,tol=2e-5):
    return abs(a-b)<=tol

def mmedian(rows,key):
    return statistics.median(x[key]for x in rows)

def validate(doc):
    if doc.get("schema_version")!=1 or doc.get("kind")!="synthetic_cpu_coalesced_candidate_reads":
        raise ValueError("Wrong record type")
    if doc.get("source_sha256")!=SOURCE:
        raise ValueError("Unpinned source")
    design=doc.get("design",{})
    if (design.get("seeds"), design.get("modes"), design.get("candidate_sizes"),
        design.get("dimensions"), design.get("queries"), design.get("repeats")) != (
            SEEDS,MODES,MVALS,D,NQ,REPS):
        raise ValueError("Experiment plan modified")
    if design.get("workloads")!=[{"vectors":n,"distribution":d}for n,d in WORKLOADS]:
        raise ValueError("Unexpected workloads")
    rows=doc.get("runs",[])
    if len(rows)!=140:
        raise ValueError("Missing the expected 140 executed trials")
    records={}
    parity={}
    for x in rows:
        n,dist,m,mode,seed=(x["vectors"],x["distribution"],x["shortlist_m"],
                             x["mode"],x["seed"])
        key=(n,dist,m,mode,seed)
        if key in records:
            raise ValueError("Duplicate trial")
        records[key]=x
        if (n,dist) not in WORKLOADS or m not in MVALS or mode not in MODES or seed not in SEEDS:
            raise ValueError("Unexpected trial metadata")
        if x.get("kind")!="synthetic_coalesced_candidate_io_cpu" or (
                x.get("status"),x.get("sanity_failures"))!=("PASS",0):
            raise ValueError("Kernel failed validation")
        if (x.get("dimensions"),x.get("queries"),x.get("repeats"),x.get("top_k"))!=(D,NQ,REPS,5):
            raise ValueError("Invalid numeric workload")
        if x.get("opportunities")!=60 or not 0<=x.get("hits",-1)<=60 or not close(
                x["recall_at5"],x["hits"]/60,1e-7):
            raise ValueError("Recall cannot be reproduced")
        for metric in ["query_p50_ms","query_p95_ms","scan_p50_ms",
                       "rerank_fetch_p50_ms","rss_after_query_kib"]:
            if x.get(metric,0)<=0:
                raise ValueError("Nonpositive measurement "+metric)
        if x.get("hint_failures")!=0:
            raise ValueError("Cache-advice syscall failure")
        if mode=="ram":
            if x["float32_resident_in_heap"] is not True or x["read_calls"]!=0 or \
               x["read_bytes"]!=0 or x["backing_file_size_bytes"]!=0:
                raise ValueError("RAM accounting inconsistent")
        else:
            if x["float32_resident_in_heap"] is not False or x["backing_file_size_bytes"]!=n*D*4:
                raise ValueError("File accounting inconsistent")
            calls_expected=m*NQ*REPS
            if x["read_bytes"]!=calls_expected*D*4:
                raise ValueError("Candidate byte count mismatch")
            if mode.startswith("pread_coalesced"):
                if x["coalesced_runs"]!=x["read_calls"] or \
                   x["read_calls"]+x["adjacent_pairs"]!=calls_expected:
                    raise ValueError("Contiguous-read accounting mismatch")
                if not 1<=x["read_calls"]<=calls_expected:
                    raise ValueError("Impossible coalesced run count")
            elif x["read_calls"]!=calls_expected or x["adjacent_pairs"]!=0 or x["coalesced_runs"]!=0:
                raise ValueError("Rank/sorted read count mismatch")
        accuracy_key=(n,dist,m,seed)
        if accuracy_key in parity and parity[accuracy_key]!=x["hits"]:
            raise ValueError("Reordering changed exact retrieval output")
        parity[accuracy_key]=x["hits"]
    if len(parity)!=20*2:
        raise ValueError("Dataset-size, seed, M combinations missing")
    overview={}
    for n,dist in WORKLOADS:
        group=f"{n}/{dist}"
        overview[group]={}
        for m in MVALS:
            modes={}
            for mode in MODES:
                selection=[records[(n,dist,m,mode,seed)] for seed in SEEDS]
                totalhits=sum(x["hits"]for x in selection)
                got=doc["summary"][group][str(m)][mode]
                if (got["cases"],got["hits"],got["top5_opportunities"])!=(5,totalhits,300):
                    raise ValueError("Published counts incorrect")
                for field,raw in [
                    ("median_query_p50_ms","query_p50_ms"),
                    ("median_query_p95_ms","query_p95_ms"),
                    ("median_rerank_fetch_p50_ms","rerank_fetch_p50_ms"),
                    ("median_rss_kib","rss_after_query_kib")
                ]:
                    if not close(got[field],mmedian(selection,raw)):
                        raise ValueError(f"Unreproducible summary {group}/{m}/{mode}/{field}")
                for field,raw in [
                    ("total_candidate_read_calls","read_calls"),
                    ("total_candidate_bytes","read_bytes"),
                    ("total_adjacencies_coalesced","adjacent_pairs"),
                    ("total_major_faults","major_faults_delta")
                ]:
                    if got[field]!=sum(x[raw]for x in selection):
                        raise ValueError("Incorrect summary counter "+field)
                if not close(got["recall_at5"],totalhits/300):
                    raise ValueError("Aggregate recall incorrect")
                modes[mode]={"p50_ms":round(mmedian(selection,"query_p50_ms"),6),
                             "read_calls":got["total_candidate_read_calls"],
                             "recall_at5":round(totalhits/300,6)}
            for mode in MODES:
                got=doc["summary"][group][str(m)][mode]
                if not close(got["ratio_to_ram_p50"],
                             modes[mode]["p50_ms"]/modes["ram"]["p50_ms"],5e-5):
                    raise ValueError("Wrong RAM ratio")
                if not close(got["ratio_to_warm_rank_p50"],
                             modes[mode]["p50_ms"]/modes["pread_rank_warm"]["p50_ms"],5e-5):
                    raise ValueError("Wrong rank ratio")
            overview[group][str(m)]=modes
    return {"status":"PASS","recorded_trials":len(rows),
            "distinct_seed_dataset_shortlist_cases":len(parity),
            "modes":MODES,"verified":overview,
            "limitations":"Synthetic single-host CPU. Warm cache likely RAM-resident. Cache hints do not force genuine cold storage."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("file",nargs="?",type=Path,
                   default=Path(__file__).parent/"results"/"2026-10-29-coalesced-reads-140-runs.json")
    args=p.parse_args()
    print(json.dumps(validate(json.loads(args.file.read_text())),indent=2))
