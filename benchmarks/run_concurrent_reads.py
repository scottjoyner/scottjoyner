#!/usr/bin/env python3
"""Bounded synchronized multi-process synthetic vector retrieval benchmark.

Each worker generates its own synthetic float32 data and anonymous backing file,
then signals readiness. A parent-created gate starts only the query loops. The
query-loop throughput metric therefore excludes generation, quantization, exact
oracle generation, and backing-file setup; it is not end-to-end RAG throughput.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import tempfile
import time

SOURCE_SHA = "445585be11c90f9c81c347d4a5b052f6d3a0b389abcc37e03e5523641dec47cd"
MODES = ["ram", "pread_rank_warm", "pread_coalesced_warm", "pread_coalesced_hint"]
DISTS = ["temporal", "clustered"]
WORKERS = [1, 2, 4]
SEEDS = [20261160, 20261161]
N, DIM, NQ, REPEATS, M = 32768, 768, 24, 4, 160
GROUP_LIMIT_SEC = 65
GLOBAL_MEM_MIN_KIB = 8 * 1024 * 1024
GLOBAL_DISK_MIN_BYTES = 8 * (1024 ** 3)


def memory_available_kib():
    with open("/proc/meminfo", encoding="utf-8") as file:
        for line in file:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    raise RuntimeError("MemAvailable missing")


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def load_receipt(stdout, dist, mode, seed):
    lines = stdout.strip().splitlines()
    if len(lines) != 2 or not lines[1].startswith("QUERY_TIMINGS_US "):
        raise ValueError("Malformed two-line worker receipt")
    row = json.loads(lines[0])
    samples = json.loads(lines[1].removeprefix("QUERY_TIMINGS_US "))
    if (
        row.get("kind") != "synthetic_concurrent_candidate_io_cpu"
        or (row.get("status"), row.get("sanity_failures")) != ("PASS", 0)
        or (row.get("distribution"), row.get("mode"), row.get("seed"),
            row.get("vectors"), row.get("dimensions"), row.get("queries"),
            row.get("repeats"), row.get("shortlist_m")) !=
            (dist, mode, seed, N, DIM, NQ, REPEATS, M)
        or row.get("total_query_count") != NQ * REPEATS
        or len(samples) != NQ * REPEATS
    ):
        raise ValueError("Worker mismatch or failed search")
    if row["query_loop_wall_ms"] <= 0 or row["query_p50_ms"] <= 0 or row["rss_after_query_kib"] <= 0:
        raise ValueError("Invalid latency or RSS")
    if not all(0 < us < 100_000_000 for us in samples):
        raise ValueError("Impossible sample values")
    if row["read_calls"] != (NQ * REPEATS * M if mode != "ram" else 0) and mode != "pread_coalesced_warm" and mode != "pread_coalesced_hint":
        raise ValueError("Unexpected ranked read count")
    if mode.startswith("pread_coalesced") and (
        row["read_calls"] + row["adjacent_pairs"] != NQ * REPEATS * M
    ):
        raise ValueError("Coalesced read accounting differs")
    if row["hint_failures"]:
        raise ValueError("Page cache hints failed")
    return row, samples


def run_group(binary, dist, mode, concurrent, seed):
    start_wall = time.monotonic()
    work = []
    with tempfile.TemporaryDirectory(prefix="sg-concurrent-gate-") as tmp:
        directory = Path(tmp)
        gate = directory / "go"
        try:
            for index in range(concurrent):
                worker_seed = seed + index
                marker = directory / f"ready-{index}"
                env = os.environ.copy()
                env["BENCH_START_GATE"] = str(gate)
                env["BENCH_READY_MARKER"] = str(marker)
                cmd = [
                    "nice", "-n", "15", str(binary), str(N), str(DIM),
                    str(NQ), str(REPEATS), str(worker_seed), dist, mode, str(M),
                ]
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, env=env,
                )
                work.append((index, proc, marker, worker_seed))
            while not all(marker.exists() for _, _, marker, _ in work):
                if time.monotonic() - start_wall > GROUP_LIMIT_SEC:
                    raise TimeoutError("Workers failed to reach query start barrier")
                if any(proc.poll() is not None for _, proc, _, _ in work):
                    raise RuntimeError("Worker exited before synchronization gate")
                time.sleep(.01)
            gate.touch(mode=0o600, exist_ok=False)
            gate_release = time.monotonic()
            receipts = []
            pooled_us = []
            for index, proc, _, worker_seed in work:
                deadline = max(5.0, GROUP_LIMIT_SEC - (time.monotonic() - start_wall))
                stdout, stderr = proc.communicate(timeout=deadline)
                if proc.returncode:
                    raise RuntimeError(
                        f"worker {index} exit {proc.returncode}: {stderr[-700:]}"
                    )
                row, durations = load_receipt(stdout, dist, mode, worker_seed)
                receipts.append(row)
                pooled_us.extend(durations)
            # The wall-clock interval from gate release through all workers finishing
            # includes polling, results serialization and process exit. This is a
            # conservative observed throughput estimate, not kernel throughput.
            gate_to_all_done_ms = (time.monotonic() - gate_release) * 1000.0
            count = len(pooled_us)
            hits = sum(w["hits"] for w in receipts)
            expected_queries = concurrent * NQ * REPEATS
            if count != expected_queries or hits < 0 or hits > concurrent * NQ * 5:
                raise ValueError("Count or accuracy mismatch")
            return {
                "distribution": dist, "mode": mode, "concurrency": concurrent,
                "seed_base": seed, "source_sha256": SOURCE_SHA,
                "query_count": count,
                "query_loop_wall_gate_to_all_done_ms": round(gate_to_all_done_ms, 6),
                "completed_queries_per_sec": round(
                    count * 1000 / gate_to_all_done_ms, 6),
                "pooled_p50_ms": round(percentile(pooled_us, .5) / 1000, 6),
                "pooled_p95_ms": round(percentile(pooled_us, .95) / 1000, 6),
                "top5_hits": hits,
                "top5_opportunities": concurrent * NQ * 5,
                "recall_at5": round(hits / (concurrent * NQ * 5), 6),
                "peak_simultaneous_process_rss_kib": sum(
                    x["rss_after_query_kib"] for x in receipts
                ),
                "query_loop_wall_max_worker_ms": max(
                    x["query_loop_wall_ms"] for x in receipts
                ),
                "total_read_calls": sum(w["read_calls"] for w in receipts),
                "total_major_faults": sum(w["major_faults_delta"] for w in receipts),
                "total_candidate_bytes": sum(w["read_bytes"] for w in receipts),
                "total_adjacent_pairs": sum(w["adjacent_pairs"] for w in receipts),
                "workers": receipts,
                "query_duration_us": pooled_us,
            }
        finally:
            for _, proc, _, _ in work:
                if proc.poll() is None:
                    proc.terminate()
            for _, proc, _, _ in work:
                if proc.poll() is None:
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()


def summarize(results):
    out = {}
    for dist in DISTS:
        out[dist] = {}
        for mode in MODES:
            out[dist][mode] = {}
            for concurrency in WORKERS:
                rows = [x for x in results if
                        (x["distribution"], x["mode"], x["concurrency"]) ==
                        (dist, mode, concurrency)]
                if sorted(x["seed_base"] for x in rows) != SEEDS:
                    raise ValueError("Missing group")
                def median(field):
                    return round(statistics.median(x[field] for x in rows), 6)
                out[dist][mode][str(concurrency)] = {
                    "replicates": len(rows),
                    "median_completed_qps": median("completed_queries_per_sec"),
                    "median_p50_ms": median("pooled_p50_ms"),
                    "median_p95_ms": median("pooled_p95_ms"),
                    "median_worker_rss_sum_kib": median(
                        "peak_simultaneous_process_rss_kib"),
                    "aggregate_recall_at5": round(
                        sum(x["top5_hits"] for x in rows) /
                        sum(x["top5_opportunities"] for x in rows), 6),
                    "total_read_calls": sum(x["total_read_calls"] for x in rows),
                }
            baseline = out[dist][mode]["1"]["median_completed_qps"]
            for c in WORKERS:
                out[dist][mode][str(c)]["qps_scaling_vs_one_worker"] = round(
                    out[dist][mode][str(c)]["median_completed_qps"] / baseline, 6)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True, type=Path)
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("C kernel SHA differs from pinned study")
    results = []
    groups = [(dist, mode, c, seed) for dist in DISTS for mode in MODES
              for c in WORKERS for seed in SEEDS]
    random.Random(20261160).shuffle(groups)
    for index, (dist, mode, concurrency, seed) in enumerate(groups, 1):
        if memory_available_kib() < GLOBAL_MEM_MIN_KIB:
            raise RuntimeError("Abort: controller below 8 GiB MemAvailable")
        if os.statvfs("/tmp").f_bavail * os.statvfs("/tmp").f_frsize < GLOBAL_DISK_MIN_BYTES:
            raise RuntimeError("Abort: temp filesystem below 8 GiB disk free")
        result = run_group(args.binary, dist, mode, concurrency, seed)
        results.append(result)
        print(
            f"PASS {index}/{len(groups)} {dist}/{mode} workers={concurrency} "
            f"seed={seed} queries={result['query_count']} "
            f"qps={result['completed_queries_per_sec']:.1f} "
            f"p95={result['pooled_p95_ms']:.3f}ms "
            f"rss={result['peak_simultaneous_process_rss_kib']}kB "
            f"recall={result['recall_at5']:.6f}", flush=True
        )
    doc = {
        "schema_version": 1, "kind": "synthetic_gated_concurrent_candidate_read_cpu",
        "date": "2026-10-29",
        "source_sha256": SOURCE_SHA,
        "source_commit": "b121ad090df96d3ecc4e9ee4c16ee7aecefdb8c2",
        "design": {
            "vectors_per_worker": N, "dimensions": DIM, "top_k": 5,
            "shortlist_m": M, "unique_queries_per_worker": NQ,
            "query_repeats": REPEATS, "modes": MODES, "distributions": DISTS,
            "concurrency": WORKERS, "seed_base_values": SEEDS,
            "max_workers": 4, "nice": 15,
        },
        "trials": results,
        "summary": summarize(results),
        "limitations": [
            "Bounded low-priority CPU workers on x1-370; not the entire fleet",
            "Each process independently builds an identical-sized synthetic in-memory index and optional anonymous float32 backing file",
            "Workers share CPU, caches and filesystem but not one shared index, queue or database service",
            "Synchronization gates query loops after each worker's generation, quantization and exact-oracle preparation",
            "Gate-to-exit throughput includes Python scheduling, worker serialization and exit after the query loop",
            "Per-query p95 pooled across repeated generated queries and workers, not independent production session arrivals",
            "Warm reads may be served by Linux page cache; fadvise hints do not ensure cold reads",
            "RSS is the sum of per-process observed RSS after queries, not system peak, total page cache or cgroup peak",
            "Production services were not stopped; hardware frequency, system load and thermal state uncontrolled",
            "No real traces, sensor media, model generation, GPU, or SensorGraft production database queried",
        ]
    }
    args.output.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print("COMPLETE", len(results), "groups", sum(x["query_count"] for x in results),
          "queries", flush=True)
    for dist, modes in doc["summary"].items():
        for mode, groups in modes.items():
            print("SUMMARY", dist, mode,
                  [(w, v["median_completed_qps"], v["median_p95_ms"],
                    v["median_worker_rss_sum_kib"], v["aggregate_recall_at5"])
                   for w, v in groups.items()], flush=True)


if __name__ == "__main__":
    main()
