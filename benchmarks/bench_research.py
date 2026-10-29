#!/usr/bin/env python3
"""Dependency-free, synthetic benchmarks for public dashcam/geospatial research.
No user media, private location traces, production DB, or GPU changes are used.
"""
import argparse
import bisect
import hashlib
import heapq
import json
import math
import os
import platform
import random
import statistics
import time
from datetime import datetime, timezone


def pct_ms(samples_ns, fraction):
    samples = sorted(samples_ns)
    return round(samples[math.ceil(fraction * len(samples)) - 1] / 1e6, 6)


def bench_calls(fn, queries, repeats):
    outputs, durations = [], []
    for turn in range(repeats):
        for query in queries:
            t0 = time.perf_counter_ns()
            answer = fn(query)
            durations.append(time.perf_counter_ns() - t0)
            if turn == 0:
                outputs.append(answer)
    return outputs, {
        "p50_ms": pct_ms(durations, 0.50),
        "p95_ms": pct_ms(durations, 0.95),
        "total_calls": len(durations),
        "total_measured_ms": round(sum(durations) / 1e6, 3),
    }


def linear_nearest(times, q):
    best_i, best_d = 0, abs(times[0] - q)
    for i in range(1, len(times)):
        d = abs(times[i] - q)
        if d < best_d:
            best_i, best_d = i, d
    return best_i


def indexed_nearest(times, q):
    i = bisect.bisect_left(times, q)
    if i == 0:
        return 0
    if i == len(times):
        return len(times) - 1
    # Equal-distance ties resolve to the earlier event, matching linear_nearest.
    return i - 1 if q - times[i - 1] <= times[i] - q else i


def geo_bench(n, nq, repeats, seed):
    rng = random.Random(seed + n)
    times = [i * 30 for i in range(n)]
    queries = [rng.randrange(-100, times[-1] + 101) for _ in range(nq)]
    baseline, bt = bench_calls(lambda q: linear_nearest(times, q), queries, repeats)
    indexed, it = bench_calls(lambda q: indexed_nearest(times, q), queries, repeats)
    mistakes = sum(a != b for a, b in zip(baseline, indexed))
    return {
        "events": n, "queries": nq, "repeats": repeats,
        "baseline": bt, "indexed": it,
        "mismatches": mistakes,
        "p50_speedup": round(bt["p50_ms"] / max(it["p50_ms"], 1e-9), 2),
        "method": "linear scan vs sorted timestamp bisect; exact event-index equality",
    }


def unit_vector(rng, dims):
    coords = [rng.gauss(0, 1) for _ in range(dims)]
    mag = math.sqrt(sum(x * x for x in coords))
    return tuple(x / mag for x in coords)


def topk(vecs, q, k):
    # Input vectors are L2-normalized; inner product is cosine similarity.
    scored = ((sum(x * y for x, y in zip(v, q)), i) for i, v in enumerate(vecs))
    return tuple(i for score, i in heapq.nlargest(k, scored))


def topk_int8(vecs, q, k):
    scored = ((sum(int(x) * int(y) for x, y in zip(v, q)), i)
              for i, v in enumerate(vecs))
    return tuple(i for score, i in heapq.nlargest(k, scored))


def vector_bench(n, dims, nq, k, repeats, seed):
    rng = random.Random(seed + 17 * n)
    vecs = [unit_vector(rng, dims) for _ in range(n)]
    queries = [unit_vector(rng, dims) for _ in range(nq)]
    quantized = [tuple(max(-127, min(127, round(x * 127))) for x in v) for v in vecs]
    q8 = [tuple(max(-127, min(127, round(x * 127))) for x in q) for q in queries]
    baseline, bt = bench_calls(lambda q: topk(vecs, q, k), queries, repeats)
    approximate, qt = bench_calls(lambda i: topk_int8(quantized, q8[i], k),
                                  list(range(nq)), repeats)
    recall = sum(len(set(a) & set(b)) / k for a, b in zip(baseline, approximate)) / nq
    return {
        "vectors": n, "dimensions": dims, "queries": nq,
        "top_k": k, "repeats": repeats,
        "float64_exact_scan": bt, "int8_quantized_scan": qt,
        "int8_recall_at_k_vs_float64": round(recall, 6),
        "theoretical_raw_payload_bytes": {
            "float64": n * dims * 8,
            "int8": n * dims,
        },
        "note": "Both use Python brute-force scans. Payload sizes exclude Python object/index overhead.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo-sizes", default="1000,10000,50000")
    ap.add_argument("--vector-sizes", default="512,2048,8192")
    ap.add_argument("--dimensions", type=int, default=48)
    ap.add_argument("--geo-queries", type=int, default=200)
    ap.add_argument("--vector-queries", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20261029)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    if min(args.dimensions, args.geo_queries, args.vector_queries, args.repeats) < 1:
        ap.error("dimensions, queries and repeats must be positive")
    geo_sizes = [int(x) for x in args.geo_sizes.split(",")]
    vector_sizes = [int(x) for x in args.vector_sizes.split(",")]
    if min(*geo_sizes, *vector_sizes) < 2:
        ap.error("all dataset sizes must be >= 2")
    results = {
        "schema_version": 1,
        "benchmark_kind": "synthetic_python_cpu_not_production_data",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor(),
        "source_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "seed": args.seed,
        "geo": [geo_bench(n, args.geo_queries, args.repeats, args.seed)
                for n in geo_sizes],
        "vectors": [vector_bench(n, args.dimensions, args.vector_queries,
                                 min(5, n), args.repeats, args.seed)
                    for n in vector_sizes],
    }
    results["status"] = ("PASS" if all(x["mismatches"] == 0
                                       for x in results["geo"]) else "FAIL")
    formatted = json.dumps(results, indent=2, sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(formatted)
    print(formatted)
    if results["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
