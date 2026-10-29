#!/usr/bin/env python3
"""Measure file-backed float32 shortlist reranking under bounded synthetic loads.

Synthetic vectors are generated on a local host, written to an anonymous
temporary file for file-backed paths, and never contain production content.
File descriptors are closed and unlinked before exit. The program uses only
best-effort page-cache eviction hints; it does NOT claim guaranteed cold I/O.
"""
import argparse
import hashlib
import json
import random
import statistics
import subprocess
from pathlib import Path

SOURCE_SHA = "5823f169d9476f5105d41c78a9d77d08a507139240554dd5b1d08f6542f2b1e5"
MODES = ["ram", "pread_warm", "pread_hint", "mmap_warm", "mmap_hint"]
MVALUES = [20, 160]
WORKLOADS = [(8192, "clustered"), (32768, "clustered")]
SEEDS = list(range(20261140, 20261145))
QUERIES = 12
REPS = 2
DIM = 768

def percentile_median(rows, key):
    return round(statistics.median(x[key] for x in rows), 6)

def validate_trial(rec, n, mode, seed, storage, m):
    if (rec.get("schema_version") != 1 or
        rec.get("kind") != "synthetic_secondary_float32_rerank_cpu" or
        (rec.get("vectors"), rec.get("dimensions"), rec.get("queries"), rec.get("repeats"),
         rec.get("distribution"), rec.get("seed"), rec.get("mode"), rec.get("shortlist_m")) !=
        (n, DIM, QUERIES, REPS, mode, seed, storage, m) or
        rec.get("sanity_failures") != 0 or rec.get("status") != "PASS"):
        raise ValueError("invalid synthetic storage trial")
    if (not 0 <= rec["hits"] <= QUERIES * 5 or
        rec["opportunities"] != QUERIES * 5 or
        abs(rec["recall_at5"] - rec["hits"] / (QUERIES * 5)) > 1e-7):
        raise ValueError("invalid recall")
    for field in ("query_p50_ms", "query_p95_ms", "scan_p50_ms", "rerank_fetch_p50_ms",
                  "rss_after_query_kib", "float32_reference_p50_ms"):
        if rec[field] <= 0:
            raise ValueError(f"invalid positive metric: {field}")
    if storage == "ram":
        if rec["backing_file_size_bytes"] != 0 or rec["read_calls"] != 0 or not rec["float32_resident_in_heap"]:
            raise ValueError("RAM trial storage mismatch")
    else:
        if rec["backing_file_size_bytes"] != n * DIM * 4 or rec["float32_resident_in_heap"]:
            raise ValueError("File-backed trial storage mismatch")
        if storage.startswith("pread") and rec["read_calls"] != REPS * QUERIES * m + m:
            raise ValueError("Pread count must include warmup and search reads")
        if storage.startswith("mmap") and rec["read_calls"] != 0:
            raise ValueError("Mapped file should not call pread")
    return rec

def summarize(receipts):
    report = {}
    for n, distribution in WORKLOADS:
        label = f"{n}/{distribution}"
        report[label] = {}
        for m in MVALUES:
            selected = [x for x in receipts if
                        (x["vectors"], x["distribution"], x["shortlist_m"]) == (n, distribution, m)]
            expected_count = len(SEEDS) * len(MODES)
            if len(selected) != expected_count:
                raise ValueError("missing workload combinations")
            by_mode = {}
            for storage in MODES:
                arr = [x for x in selected if x["mode"] == storage]
                if sorted(x["seed"] for x in arr) != SEEDS:
                    raise ValueError("missing seed or duplicate")
                hits = sum(x["hits"] for x in arr)
                by_mode[storage] = {
                    "runs": len(arr),
                    "top5_hits": hits,
                    "top5_opportunities": QUERIES * 5 * len(arr),
                    "recall_at5": round(hits / (QUERIES * 5 * len(arr)), 6),
                    "median_query_p50_ms": percentile_median(arr, "query_p50_ms"),
                    "median_query_p95_ms": percentile_median(arr, "query_p95_ms"),
                    "median_rss_after_query_kib": percentile_median(arr, "rss_after_query_kib"),
                    "median_quantization_ms": percentile_median(arr, "quantization_ms"),
                    "median_backing_file_setup_ms": percentile_median(arr, "backing_file_setup_ms"),
                    "sum_major_page_faults": sum(x["major_faults_delta"] for x in arr),
                    "total_hint_failures": sum(x["hint_failures"] for x in arr),
                }
            base = by_mode["ram"]
            for path, item in by_mode.items():
                item["query_p50_ratio_vs_ram"] = round(
                    item["median_query_p50_ms"] / base["median_query_p50_ms"], 5
                )
                item["process_rss_fraction_of_ram"] = round(
                    item["median_rss_after_query_kib"] / base["median_rss_after_query_kib"], 5
                )
            report[label][str(m)] = by_mode
    return report

def run(args):
    src_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if src_hash != SOURCE_SHA:
        raise ValueError("C source changed after freezing workload")
    data = []
    for n, distribution in WORKLOADS:
        for seed in SEEDS:
            # Rotate measurement order to reduce systematic warm-order bias.
            cases = [(m, storage) for m in MVALUES for storage in MODES]
            random.Random(seed + n).shuffle(cases)
            for m, storage in cases:
                c = [str(args.binary), str(n), str(DIM), str(QUERIES),
                     str(REPS), str(seed), distribution, storage, str(m)]
                p = subprocess.run(c, check=True, capture_output=True, text=True, timeout=65)
                entry = validate_trial(json.loads(p.stdout), n, distribution, seed, storage, m)
                data.append(entry)
                print(f"PASS {n}/{distribution} seed={seed} M={m} {storage} "
                      f"p50={entry['query_p50_ms']:.4f}ms rss={entry['rss_after_query_kib']}kB "
                      f"recall={entry['recall_at5']:.4f}", flush=True)
    # Verify the same generator/seed has identical retrieval results on all storage paths.
    for n, distribution in WORKLOADS:
        for seed in SEEDS:
            for m in MVALUES:
                runs = [r for r in data if (r["vectors"], r["distribution"],
                                             r["seed"], r["shortlist_m"]) ==
                                            (n, distribution, seed, m)]
                if len(runs) != len(MODES) or len(set(r["hits"] for r in runs)) != 1:
                    raise ValueError("Cross-mode exact result parity failed")
    doc = {
        "schema_version": 1, "kind": "synthetic_secondary_float32_rerank_storage_study",
        "date": "2026-10-29", "source_sha256": src_hash,
        "source_commit": "a957936ce1d9b39e98dff2c9522390320646cced",
        "workloads": [{"n": n, "distribution": d} for n, d in WORKLOADS],
        "seed_values": SEEDS, "modes": MODES, "shortlist_sizes": MVALUES,
        "dimensions": DIM, "queries": QUERIES, "repeats": REPS,
        "raw_trials": data, "summary": summarize(data),
        "methodology": [
            "Each trial runs in a fresh Linux process with deterministic synthetic normalized vectors.",
            "Int8 per-vector absmax vectors and scales remain in process RAM.",
            "The RAM baseline keeps float32 vectors in the same process.",
            "File-backed modes write an anonymous regular file with float32 vectors and free the source float32 heap allocation before measuring.",
            "Pread modes fetch M complete float32 vectors individually for every query; mmap modes use mapped pointers.",
            "Warm modes use cached pages, including pages potentially already in cache from initial writes.",
            "Hint modes fsync the file before queries and request best-effort page-cache eviction with fadvise and madvise; hints may not guarantee cold reads.",
            "RSS is process-level resident memory, not system-wide RAM/page-cache, peak memory, or memory/cgroup accounting.",
            "Synthetic generation, quantization, index/build and backing file setup are separate from query latency.",
            "No production content, network trace, GPU, Neo4j or model execution was accessed.",
            "All modes compute the same synthetic top-5 recall, matched to a full exact float32 oracle created before file-backed float32 buffers are released.",
        ],
    }
    args.output.write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8")
    print("FINAL_SUMMARY", json.dumps(doc["summary"], separators=(",", ":")), flush=True)
    print("SAVED", args.output, "runs", len(data), flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    run(ap.parse_args())
