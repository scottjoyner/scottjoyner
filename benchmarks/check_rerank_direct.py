#!/usr/bin/env python3
"""Validate directly timed synthetic int8 candidate-scan/float32 rerank fleet results."""
import argparse
import json
import statistics
from pathlib import Path

SHA = "6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec"
MODES = ["independent", "temporal", "clustered"]
SEEDS = [20261029, 20261030, 20261031, 20261032, 20261033]
CANDIDATES = [5, 10, 20, 40, 80, 160]


def validate(document):
    if document.get("kind") != "synthetic_direct_timed_shortlist_multihost":
        raise ValueError("Wrong benchmark kind")
    if document.get("source_sha256") != SHA or document.get("seed_values") != SEEDS:
        raise ValueError("Source or seed mismatch")
    runs = document.get("runs", [])
    if len(runs) != 3 or len({host["node"] for host in runs}) != 3:
        raise ValueError("Need three unique hosts")
    reference = None
    all_hosts = {}
    for host in runs:
        cases = host.get("trials", [])
        if len(cases) != 15:
            raise ValueError("Missing trials for " + host["node"])
        lookup = {(c["distribution"], c["seed"]): c for c in cases}
        if len(lookup) != 15:
            raise ValueError("Duplicate distribution/seed case")
        rec = {}
        per_mode = {}
        for mode in MODES:
            cases_for_mode = []
            for seed in SEEDS:
                row = lookup.get((mode, seed))
                if not row or row.get("status") != "PASS" or row.get("sanity_failures") != 0:
                    raise ValueError("Invalid trial")
                if row.get("kind") != "synthetic_cpu_int8_direct_shortlist_float32_rerank":
                    raise ValueError("Unexpected trial kind")
                if (row["vectors"], row["dimensions"], row["queries"], row["repeats"], row["top_k"]) != (8192,768,12,2,5):
                    raise ValueError("Workload mismatch")
                if [q["candidates"] for q in row["options"]] != CANDIDATES:
                    raise ValueError("Candidate size mismatch")
                recalls = [q["recall_at_5"] for q in row["options"]]
                if any(not 0 <= r <= 1 for r in recalls):
                    raise ValueError("Invalid recall")
                if any(recalls[i] > recalls[i+1] + 1e-6 for i in range(5)):
                    raise ValueError("Increasing shortlist reduced recall")
                for x in row["options"]:
                    if (x["int8_scan_p50_ms"] <= 0 or x["rerank_only_p50_ms"] <= 0 or
                            x["end_to_end_p50_ms"] <= 0):
                        raise ValueError("Nonpositive latency")
                    if x["end_to_end_p50_ms"] < x["int8_scan_p50_ms"] * 0.80:
                        raise ValueError("Implausible full-stage timing")
                rec[f"{mode}/{seed}"] = recalls
                cases_for_mode.append(row)
            per_mode[mode] = {
                str(m): {
                    "mean_recall_at_5": round(statistics.mean(r["options"][j]["recall_at_5"] for r in cases_for_mode),6),
                    "median_direct_query_p50_ms": round(statistics.median(r["options"][j]["end_to_end_p50_ms"] for r in cases_for_mode),6),
                } for j,m in enumerate(CANDIDATES)
            }
            per_mode[mode]["exact_float32_p50_ms"] = round(
                statistics.median(r["exact_float32_p50_ms"] for r in cases_for_mode),6
            )
        if reference is None:
            reference = rec
        elif rec != reference:
            raise ValueError("Identical data differs in exact recall across hosts")
        all_hosts[host["node"]] = per_mode
    return {
        "status": "PASS",
        "hosts": len(runs),
        "recorded_runs": sum(len(h["trials"]) for h in runs),
        "distinct_seed_distribution_cases": len(SEEDS)*len(MODES),
        "by_host": all_hosts,
        "scope": "synthetic CPU scan and rerank, prequantized inputs; not production database/GPU",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?",type=Path,
                    default=Path(__file__).parent/"results"/"2026-10-29-rerank-direct-multihost.json")
    args=ap.parse_args()
    print(json.dumps(validate(json.loads(args.file.read_text())),indent=2))
