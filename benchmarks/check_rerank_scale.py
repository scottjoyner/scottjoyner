#!/usr/bin/env python3
"""Validate large synthetic 32768 x 768 direct-timing shortlist trials."""
import argparse
import json
import statistics
from pathlib import Path

SOURCE_SHA = "6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec"
SEEDS = [20261029, 20261030, 20261031, 20261032, 20261033]
MODES = ["independent", "clustered"]
CANDIDATES = [5, 10, 20, 40, 80, 160]


def validate(doc):
    if doc.get("kind") != "synthetic_direct_rerank_32k_cpu_scale":
        raise ValueError("Wrong benchmark kind")
    if doc.get("source_sha256") != SOURCE_SHA or doc.get("seed_values") != SEEDS:
        raise ValueError("Source hash or seeds mismatch")
    if (doc.get("vectors"), doc.get("dimensions"), doc.get("modes")) != (32768, 768, MODES):
        raise ValueError("Workload differs")
    trials = doc.get("trials", [])
    if len(trials) != 10:
        raise ValueError("Expected ten seeded trials")
    by_mode = {}
    for mode in MODES:
        data = []
        for seed in SEEDS:
            matching = [r for r in trials if r.get("seed") == seed and r.get("distribution") == mode]
            if len(matching) != 1:
                raise ValueError("Missing/duplicate case")
            r = matching[0]
            if r.get("status") != "PASS" or r.get("sanity_failures") != 0:
                raise ValueError("Sanity failed")
            if (r.get("vectors"),r.get("dimensions"),r.get("queries"),r.get("repeats")) != (32768,768,12,2):
                raise ValueError("Trial workload mismatch")
            choices = r.get("options", [])
            if [v.get("candidates") for v in choices] != CANDIDATES:
                raise ValueError("Candidate count mismatch")
            recalls = [x["recall_at_5"] for x in choices]
            if any(not 0 <= x <= 1 for x in recalls):
                raise ValueError("Out-of-range recall")
            if any(recalls[i+1]+1e-6 < recalls[i] for i in range(5)):
                raise ValueError("Increasing shortlist decreased recall")
            if not all(x["end_to_end_p50_ms"] > 0 for x in choices):
                raise ValueError("Invalid timings")
            data.append(r)
        by_mode[mode] = {
            "mean_recall_at_5_by_m": {
                str(m): round(statistics.mean(r["options"][i]["recall_at_5"] for r in data),6)
                for i,m in enumerate(CANDIDATES)
            },
            "median_exact_float32_ms": round(statistics.median(r["exact_float32_p50_ms"] for r in data),6),
            "median_direct_m160_ms": round(statistics.median(r["options"][5]["end_to_end_p50_ms"] for r in data),6),
            "median_one_time_quantization_ms": round(statistics.median(r["quantize_vectors_and_queries_ms"] for r in data),6),
        }
    return {
        "status": "PASS", "distinct_seed_distribution_cases": len(trials),
        "results": by_mode,
        "caveat": "One host and ten synthetic datasets, no real embeddings or GPU, index/build excluded",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", type=Path,
                    default=Path(__file__).parent/"results"/"2026-10-29-rerank-direct-32768-x1-370.json")
    args = ap.parse_args()
    print(json.dumps(validate(json.loads(args.path.read_text(encoding="utf-8"))),indent=2))
