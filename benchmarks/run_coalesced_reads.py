#!/usr/bin/env python3
"""Run synthetic CPU float32 candidate-IO comparison with read-count parity.

Fresh low-priority processes per seed/mode; source data and query vectors
are synthetic, the float32 file is anonymous and unlinked on creation.
"""
import argparse
import hashlib
import json
import random
import statistics
import subprocess
from pathlib import Path

SOURCE_SHA = "d2f4ed078d87bff565dcc26e74f67c3967b801311ac08087b27b915159496c4e"
MODES = [
    "ram", "pread_rank_warm", "pread_sorted_warm", "pread_coalesced_warm",
    "pread_rank_hint", "pread_sorted_hint", "pread_coalesced_hint"
]
WORKLOADS = [(8192, "temporal"), (8192, "clustered"),
             (32768, "temporal"), (32768, "clustered")]
CANDIDATES = [20, 160]
SEEDS = [20261150, 20261151, 20261152, 20261153, 20261154]
D = 768
NQ, REPS = 12, 2

def validate_row(x, n, dist, seed, m, mode):
    if (x.get("kind") != "synthetic_coalesced_candidate_io_cpu" or
        x.get("status") != "PASS" or x.get("sanity_failures") != 0 or
        (x.get("vectors"), x.get("dimensions"), x.get("queries"),
         x.get("repeats"), x.get("distribution"), x.get("seed"),
         x.get("mode"), x.get("shortlist_m")) !=
        (n, D, NQ, REPS, dist, seed, mode, m)):
        raise ValueError("Incorrect benchmark evidence")
    if not 0 <= x.get("hits", -1) <= NQ * 5 or x.get("opportunities") != NQ * 5 or abs(
            x["recall_at5"] - x["hits"] / (NQ * 5)) > 1e-7:
        raise ValueError("Incorrect top5 recall")
    if any(x.get(k, 0) <= 0 for k in [
            "query_p50_ms", "query_p95_ms", "scan_p50_ms",
            "rerank_fetch_p50_ms", "rss_after_query_kib"]):
        raise ValueError("Invalid runtime measurement")
    if mode == "ram":
        if x["read_calls"] or x["backing_file_size_bytes"] or not x["float32_resident_in_heap"]:
            raise ValueError("RAM mode did file reads")
    else:
        if x["float32_resident_in_heap"] or x["backing_file_size_bytes"] != n*D*4:
            raise ValueError("File-backed allocation mismatch")
        if x["read_bytes"] != NQ * REPS * m * D * 4:
            raise ValueError("Mismatched byte totals")
        reads = NQ * REPS * m
        if mode.startswith("pread_coalesced_"):
            if x["read_calls"] + x["adjacent_pairs"] != reads:
                raise ValueError("Coalesced reads did not account for contiguous IDs")
            if x["coalesced_runs"] != x["read_calls"]:
                raise ValueError("Coalesced run count mismatch")
        else:
            if x["read_calls"] != reads or x["adjacent_pairs"] or x["coalesced_runs"]:
                raise ValueError("Unexpected read accounting")
    if x.get("hint_failures") != 0:
        raise ValueError("Cache hint failed")
    return x

def median(rows, name):
    return round(statistics.median(x[name] for x in rows), 6)

def summarize(rows):
    output = {}
    for n, dist in WORKLOADS:
        group = f"{n}/{dist}"
        output[group] = {}
        for m in CANDIDATES:
            per_mode = {}
            for mode in MODES:
                selected = [r for r in rows if
                            (r["vectors"], r["distribution"], r["shortlist_m"], r["mode"])
                            == (n, dist, m, mode)]
                if sorted(x["seed"] for x in selected) != SEEDS:
                    raise ValueError("Missing seed")
                found = sum(x["hits"] for x in selected)
                per_mode[mode] = {
                    "cases": len(selected),
                    "recall_at5": round(found / (len(selected)*NQ*5), 6),
                    "hits": found,
                    "top5_opportunities": len(selected)*NQ*5,
                    "median_query_p50_ms": median(selected, "query_p50_ms"),
                    "median_query_p95_ms": median(selected, "query_p95_ms"),
                    "median_rerank_fetch_p50_ms": median(selected, "rerank_fetch_p50_ms"),
                    "median_rss_kib": median(selected, "rss_after_query_kib"),
                    "total_candidate_read_calls": sum(x["read_calls"] for x in selected),
                    "total_candidate_bytes": sum(x["read_bytes"] for x in selected),
                    "total_adjacencies_coalesced": sum(x["adjacent_pairs"] for x in selected),
                    "total_major_faults": sum(x["major_faults_delta"] for x in selected),
                }
            ram_t = per_mode["ram"]["median_query_p50_ms"]
            rank_t = per_mode["pread_rank_warm"]["median_query_p50_ms"]
            for mode in MODES:
                per_mode[mode]["ratio_to_ram_p50"] = round(
                    per_mode[mode]["median_query_p50_ms"] / ram_t, 6)
                per_mode[mode]["ratio_to_warm_rank_p50"] = round(
                    per_mode[mode]["median_query_p50_ms"] / rank_t, 6)
            output[group][str(m)] = per_mode
    return output

def run(args):
    digest = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA:
        raise ValueError("Pinned source SHA mismatch")
    results = []
    for n, dist in WORKLOADS:
        for seed in SEEDS:
            workload = [(m, mode) for m in CANDIDATES for mode in MODES]
            random.Random(n + seed).shuffle(workload)
            for m, mode in workload:
                command = [str(args.binary), str(n), str(D), str(NQ),
                           str(REPS), str(seed), dist, mode, str(m)]
                p = subprocess.run(command, capture_output=True, check=True,
                                   text=True, timeout=65)
                x = validate_row(json.loads(p.stdout), n, dist, seed, m, mode)
                results.append(x)
                print(f"PASS {n}/{dist} seed={seed} M={m} mode={mode} "
                      f"p50={x['query_p50_ms']:.4f}ms calls={x['read_calls']} "
                      f"hits={x['hits']}", flush=True)
    for n, dist in WORKLOADS:
        for seed in SEEDS:
            for m in CANDIDATES:
                rows = [x for x in results if
                        (x["vectors"], x["distribution"], x["seed"], x["shortlist_m"])
                        == (n, dist, seed, m)]
                if len(rows) != len(MODES) or len({x["hits"] for x in rows}) != 1:
                    raise ValueError(f"Top5 parity failed: {n}/{dist}/{seed}/{m}")
    evidence = {
        "schema_version": 1,
        "kind": "synthetic_cpu_coalesced_candidate_reads",
        "date": "2026-10-29",
        "source_sha256": SOURCE_SHA,
        "source_commit": "8d811446ebc5c36c89844ab307faf37619d190e8",
        "design": {
            "workloads": [{"vectors": n, "distribution": dist} for n, dist in WORKLOADS],
            "seeds": SEEDS, "modes": MODES, "candidate_sizes": CANDIDATES,
            "dimensions": D, "queries": NQ, "repeats": REPS,
            "backend": "anonymous temporary file on host filesystem",
            "coalescing": "sort candidate IDs and read consecutive float32 vector records with one pread"
        },
        "runs": results,
        "summary": summarize(results),
        "limitations": [
            "CPU synthetic distributions and self-contained temporary files only",
            "Same five seeds repeated across seven storage modes; 140 executions are 20 distinct seed/distribution/size cases, times two M choices",
            "Warm paths may be served from the Linux kernel page cache",
            "Eviction-hint paths do not guarantee cold SSD I/O",
            "Process RSS excludes Linux page cache and system-wide memory",
            "No real embeddings, production SensorGraft graph, GPU, or network I/O",
            "No concurrency; no reference-frame corruption, update or durability testing",
            "Indexed graph/vector retrieval and embedding construction are not measured",
            "Independent subprocesses reduce interference but do not control system scheduling or cache",
            "Temporary file is unlinked; no production files are read or modified"
        ]
    }
    args.output.write_text(json.dumps(evidence, separators=(",", ":")) + "\n")
    print("COMPLETE", len(results), "runs", flush=True)
    for group, modes in evidence["summary"].items():
        for m, record in modes.items():
            print("SUMMARY", group, m, "RAM",
                  record["ram"]["median_query_p50_ms"],
                  "warm_rank", record["pread_rank_warm"]["median_query_p50_ms"],
                  "warm_sorted", record["pread_sorted_warm"]["median_query_p50_ms"],
                  "warm_coalesced", record["pread_coalesced_warm"]["median_query_p50_ms"],
                  "hint_rank", record["pread_rank_hint"]["median_query_p50_ms"],
                  "hint_coalesced", record["pread_coalesced_hint"]["median_query_p50_ms"],
                  "calls_coalesced", record["pread_coalesced_warm"]["total_candidate_read_calls"],
                  "calls_rank", record["pread_rank_warm"]["total_candidate_read_calls"],
                  flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--binary", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    run(ap.parse_args())
