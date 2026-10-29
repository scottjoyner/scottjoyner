#!/usr/bin/env python3
"""Second disjoint validation set for post-hoc revised synthetic shortlist policy.

Policy was selected after the first held-out 32K experiment. Seeds 20261054+
were not used in calibration or the first holdout. This does NOT establish
real-world query performance or privacy-safe production readiness.
"""
import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path

SOURCE_SHA = "6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec"
SEED_START = 20261054
CANDIDATES = [5, 10, 20, 40, 80, 160]
MODES = ["independent", "clustered"]
# Fixed before accessing the second set, selected from the first heldout:
POLICY_V1 = {"independent": 10, "clustered": 40}
POLICY_V2 = {"independent": 20, "clustered": 80}
N = 32768
D = 768
QUERIES = 12
REPEATS = 2
TOPK = 5


def read_source(source):
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != SOURCE_SHA:
        raise ValueError("C source does not match pinned experiment")
    return sha


def summarize(rows):
    summary = {}
    for mode in MODES:
        samples = [x for x in rows if x["mode"] == mode]
        if not samples:
            raise ValueError(f"no samples: {mode}")
        total = len(samples) * QUERIES * TOPK
        mdata = {}
        for j, m in enumerate(CANDIDATES):
            scores = [r["options"][j] for r in samples]
            hits = sum(round(x["recall_at_5"] * QUERIES * TOPK) for x in scores)
            mdata[str(m)] = {
                "hits": hits,
                "top5_opportunities": total,
                "recall_at_5": round(hits / total, 6),
                "min_case_recall_at_5": min(x["recall_at_5"] for x in scores),
                "median_direct_query_p50_ms": round(
                    statistics.median(x["direct_query_p50_ms"] for x in scores), 6),
            }
        baseline = statistics.median(r["exact_float32_p50_ms"] for r in samples)
        setup = statistics.median(r["prequery_quantize_ms"] for r in samples)
        new_m = POLICY_V2[mode]
        new_ms = mdata[str(new_m)]["median_direct_query_p50_ms"]
        savings = baseline - new_ms
        summary[mode] = {
            "old_policy_m": POLICY_V1[mode],
            "new_policy_m_frozen_before_second_holdout": new_m,
            "old_policy": mdata[str(POLICY_V1[mode])],
            "new_policy": mdata[str(new_m)],
            "new_policy_pass_99pct_recall": mdata[str(new_m)]["hits"] / total >= .99,
            "exact_float32_median_p50_ms": round(baseline, 6),
            "one_time_quantize_median_ms": round(setup, 6),
            "new_policy_nominal_median_speedup": round(baseline / new_ms, 4),
            "new_policy_nominal_quantization_break_even_queries":
                math.ceil(setup/savings) if savings > 0 else None,
            "all_candidate_sizes": mdata,
        }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not 1 <= args.count <= 50:
        parser.error("count must be 1..50")
    read_source(args.source)
    seeds = list(range(SEED_START, SEED_START + args.count))
    output = []
    print("PRECOMMITTED policy_v2=" + json.dumps(POLICY_V2, sort_keys=True), flush=True)
    for mode in MODES:
        for seed in seeds:
            p = subprocess.run(
                [str(args.binary), str(N), str(D), str(QUERIES),
                 str(REPEATS), str(seed), mode],
                capture_output=True, text=True, check=True, timeout=65)
            row = json.loads(p.stdout)
            if (row.get("status") != "PASS" or row.get("sanity_failures") != 0
                    or (row["seed"], row["distribution"], row["vectors"],
                        row["dimensions"], row["queries"], row["repeats"])
                    != (seed, mode, N, D, QUERIES, REPEATS)
                    or [v["candidates"] for v in row["options"]] != CANDIDATES):
                raise ValueError(f"Invalid trial for {mode}/{seed}")
            vals = [z["recall_at_5"] for z in row["options"]]
            if any(not 0 <= val <= 1 for val in vals) or any(
                    vals[i] > vals[i+1]+1e-6 for i in range(len(vals)-1)):
                raise ValueError("Recall invalid or non-monotonic")
            output.append({
                "seed": seed, "mode": mode,
                "exact_float32_p50_ms": row["exact_float32_p50_ms"],
                "prequery_quantize_ms": row["quantize_vectors_and_queries_ms"],
                "options": [{
                    "m": v["candidates"],
                    "recall_at_5": v["recall_at_5"],
                    "direct_query_p50_ms": v["end_to_end_p50_ms"]
                } for v in row["options"]],
            })
            selected = row["options"][CANDIDATES.index(POLICY_V2[mode])]
            print(f"PASS mode={mode} seed={seed} M={POLICY_V2[mode]} "
                  f"recall={selected['recall_at_5']:.6f} "
                  f"p50_ms={selected['end_to_end_p50_ms']:.4f}", flush=True)
    doc = {
        "schema_version": 1, "kind": "synthetic_cpu_second_disjoint_holdout",
        "date": "2026-10-29", "benchmark_host": "x1-370",
        "vectors": N, "dimensions": D, "queries": QUERIES, "repeats": REPEATS,
        "c_source_sha256": SOURCE_SHA, "seed_start": SEED_START,
        "seed_values": seeds,
        "policy_v1_failed_first_holdout": POLICY_V1,
        "policy_v2_precommitted_to_second_holdout": POLICY_V2,
        "records": output, "summary": summarize(output),
        "limitations": [
            "Synthetic CPU-only, no real dashcam, GNSS, traces or private data",
            "V2 policy was selected after seeing first holdout and evaluated once on a disjoint second holdout",
            "Same distribution generators as earlier study; not out-of-distribution generalization",
            "Top-five hits across queries are not statistically independent claims about real retrieval",
            "End-to-end here means int8 prequantized scan plus float32 rerank, not end-to-end RAG or database query",
            "Quantization/preprocessing costs excluded from query p50 but reported separately",
        ],
    }
    args.out.write_text(json.dumps(doc, separators=(",", ":"))+"\n", encoding="utf-8")
    print(json.dumps({
        "evidence": str(args.out), "runs": len(output),
        "summary": doc["summary"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
