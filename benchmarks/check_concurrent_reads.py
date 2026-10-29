#!/usr/bin/env python3
"""Recompute synchronized concurrent CPU retrieval evidence from recorded receipts.

Validates 48 gated workload groups, 112 worker processes and 10,752 timed
synthetic queries, plus pooled p95, page-fault/read counts and process RSS.
"""
import argparse
import json
import statistics
from pathlib import Path

SOURCE = "445585be11c90f9c81c347d4a5b052f6d3a0b389abcc37e03e5523641dec47cd"
MODES = ["ram", "pread_rank_warm", "pread_coalesced_warm", "pread_coalesced_hint"]
DISTS = ["temporal", "clustered"]
COUNTS = [1, 2, 4]
SEEDS = [20261160, 20261161]
N, DIM, NQ, REPS, M = 32768, 768, 24, 4, 160

def close(x, y, tol=0.00002):
    return abs(x - y) <= tol

def pctl(values, fraction):
    arr = sorted(values)
    return arr[int(fraction * (len(arr) - 1))]

def verify(doc):
    if doc.get("kind") != "synthetic_gated_concurrent_candidate_read_cpu" or doc.get("schema_version") != 1:
        raise ValueError("Artifact kind or schema mismatch")
    if doc.get("source_sha256") != SOURCE:
        raise ValueError("Source code fingerprint mismatch")
    d = doc.get("design", {})
    if (d.get("vectors_per_worker"), d.get("dimensions"), d.get("shortlist_m"),
        d.get("unique_queries_per_worker"), d.get("query_repeats"), d.get("modes"),
        d.get("distributions"), d.get("concurrency"), d.get("seed_base_values")) != (
        N, DIM, M, NQ, REPS, MODES, DISTS, COUNTS, SEEDS
    ):
        raise ValueError("Experiment design mismatch")
    rows = doc.get("trials", [])
    if len(rows) != 48:
        raise ValueError("Expected 48 gated groups")
    evidence = {}
    distinct = set()
    workers = 0
    total_queries = 0
    accuracy = {}
    for group in rows:
        dist, mode, count, base = (group["distribution"], group["mode"],
                                   group["concurrency"], group["seed_base"])
        key = (dist, mode, count, base)
        if key in distinct:
            raise ValueError("Duplicate workload group")
        distinct.add(key)
        if dist not in DISTS or mode not in MODES or count not in COUNTS or base not in SEEDS:
            raise ValueError("Unexpected workload group")
        if group["source_sha256"] != SOURCE:
            raise ValueError("Trial source mismatch")
        trial_workers = group.get("workers", [])
        if len(trial_workers) != count:
            raise ValueError("Missing synchronized workers")
        queries = group.get("query_duration_us", [])
        if len(queries) != NQ * REPS * count or group["query_count"] != len(queries):
            raise ValueError("Invalid number of pooled query timings")
        if any(q <= 0 for q in queries):
            raise ValueError("Invalid query duration")
        if not close(group["pooled_p50_ms"], pctl(queries, .5) / 1000) or not close(
            group["pooled_p95_ms"], pctl(queries, .95) / 1000
        ):
            raise ValueError("Incorrect pooled latency percentiles")
        if not close(group["completed_queries_per_sec"],
                     len(queries) * 1000 / group["query_loop_wall_gate_to_all_done_ms"], .0001):
            raise ValueError("Throughput not reproduced from gate wall-clock interval")
        for i, worker in enumerate(trial_workers):
            if worker.get("kind") != "synthetic_concurrent_candidate_io_cpu":
                raise ValueError("Worker kind mismatch")
            if (worker.get("status"), worker.get("sanity_failures")) != ("PASS", 0):
                raise ValueError("Worker failed correctness")
            if (worker["vectors"], worker["dimensions"], worker["queries"],
                worker["repeats"], worker["seed"], worker["distribution"],
                worker["mode"], worker["shortlist_m"], worker["total_query_count"]) != (
                N, DIM, NQ, REPS, base + i, dist, mode, M, NQ*REPS
            ):
                raise ValueError("Wrong worker dataset/seed")
            if worker["hint_failures"] != 0:
                raise ValueError("Failed eviction hints")
            if (worker["top_k"], worker["opportunities"]) != (5, NQ*5) or not (
                0 <= worker["hits"] <= NQ*5
            ) or not close(worker["recall_at5"], worker["hits"]/(NQ*5), .000001):
                raise ValueError("Worker retrieval hits incorrect")
            recall_key = (dist, base + i)
            if recall_key in accuracy and accuracy[recall_key] != worker["hits"]:
                raise ValueError("Same synthetic dataset differs between retrieval paths")
            accuracy[recall_key] = worker["hits"]
            if (worker["read_calls"] != 0 and mode == "ram") or (
                mode != "ram" and worker["read_bytes"] != NQ*REPS*M*DIM*4
            ):
                raise ValueError("Inconsistent candidate IO")
            if mode == "pread_rank_warm" and worker["read_calls"] != NQ*REPS*M:
                raise ValueError("Wrong rank read count")
            if mode.startswith("pread_coalesced") and (
                worker["read_calls"] + worker["adjacent_pairs"] != NQ*REPS*M
            ):
                raise ValueError("Wrong coalesced IO accounting")
        total_hits = sum(x["hits"] for x in trial_workers)
        total_opps = count * NQ * 5
        if (group["top5_hits"], group["top5_opportunities"]) != (total_hits, total_opps):
            raise ValueError("Group hit count differs from workers")
        if not close(group["recall_at5"], total_hits/total_opps, .000001):
            raise ValueError("Group recall incorrect")
        if group["total_read_calls"] != sum(x["read_calls"] for x in trial_workers):
            raise ValueError("IO calls not reconciled")
        if group["total_candidate_bytes"] != sum(x["read_bytes"] for x in trial_workers):
            raise ValueError("IO bytes not reconciled")
        if group["total_adjacent_pairs"] != sum(x["adjacent_pairs"] for x in trial_workers):
            raise ValueError("Coalescence not reconciled")
        if group["total_major_faults"] != sum(x["major_faults_delta"] for x in trial_workers):
            raise ValueError("Page fault count not reconciled")
        if group["peak_simultaneous_process_rss_kib"] != sum(x["rss_after_query_kib"] for x in trial_workers):
            raise ValueError("Sum of worker RSS mismatch")
        if not close(group["query_loop_wall_max_worker_ms"],
                     max(x["query_loop_wall_ms"] for x in trial_workers)):
            raise ValueError("Worker query loop wall time mismatch")
        workers += count
        total_queries += len(queries)
    expected = {(d, m, c, seed) for d in DISTS for m in MODES for c in COUNTS for seed in SEEDS}
    if distinct != expected:
        raise ValueError("Missing workload combinations")
    if workers != 112 or total_queries != 10752:
        raise ValueError("Unexpected overall worker/query count")
    compact = {}
    for dist in DISTS:
        compact[dist] = {}
        for mode in MODES:
            compact[dist][mode] = {}
            for count in COUNTS:
                subset = [x for x in rows if (x["distribution"],x["mode"],x["concurrency"]) ==
                          (dist,mode,count)]
                got = doc["summary"][dist][mode][str(count)]
                def med(field):
                    return statistics.median(x[field] for x in subset)
                expected_fields = [
                    ("median_completed_qps","completed_queries_per_sec"),
                    ("median_p50_ms","pooled_p50_ms"),
                    ("median_p95_ms","pooled_p95_ms"),
                    ("median_worker_rss_sum_kib","peak_simultaneous_process_rss_kib")
                ]
                if got["replicates"] != 2:
                    raise ValueError("Summary replicate count wrong")
                for field, raw_field in expected_fields:
                    if not close(got[field], med(raw_field)):
                        raise ValueError(f"Summary incorrect: {dist}/{mode}/{count}/{field}")
                hits = sum(x["top5_hits"] for x in subset)
                opp = sum(x["top5_opportunities"] for x in subset)
                if not close(got["aggregate_recall_at5"], hits/opp, .000001):
                    raise ValueError("Summary recall mismatched")
                compact[dist][mode][str(count)] = {
                    "qps": round(med("completed_queries_per_sec"), 3),
                    "pooled_p95_ms": round(med("pooled_p95_ms"), 3),
                    "recall_at5": round(hits/opp, 6),
                }
            baseline = doc["summary"][dist][mode]["1"]["median_completed_qps"]
            for count in COUNTS:
                record = doc["summary"][dist][mode][str(count)]
                if not close(record["qps_scaling_vs_one_worker"],
                             record["median_completed_qps"]/baseline, .0001):
                    raise ValueError("Incorrect relative scalability")
    return {
        "status": "PASS", "concurrency_groups": len(rows),
        "actual_worker_processes": workers,
        "completed_query_executions": total_queries,
        "distinct_synthetic_seed_distribution_cases": len(accuracy),
        "verified": compact,
        "scope": "Synthetic CPU independent workers with gated query loops; no single shared production index",
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", type=Path,
                        default=Path(__file__).parent / "results" /
                        "2026-10-29-concurrent-candidate-io.json")
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.file.read_text(encoding="utf-8"))), indent=2))
