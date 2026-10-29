#!/usr/bin/env python3
"""Held-out synthetic shortlist calibration and direct CPU benchmark.

Fits a *fixed* top-M policy using the existing five-seed receipts, then
runs previously unseen seeds. Does not use production data or GPU resources.
"""
import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path

SOURCE_SHA = "6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec"
CANDIDATES = [5, 10, 20, 40, 80, 160]
CALIBRATION_SEEDS = list(range(20261029, 20261034))
HOLDOUT_SEED_START = 20261034
QUERIES = 12
REPEATS = 2
TOPK = 5
TARGET = 0.99


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def calibration_policy(file, n, modes):
    record = json.loads(file.read_text(encoding="utf-8"))
    if n == 8192:
        trials = record["runs"][0]["trials"]
        assert record["seed_values"] == CALIBRATION_SEEDS
    elif n == 32768:
        trials = record["trials"]
        assert record["seed_values"] == CALIBRATION_SEEDS
    else:
        raise ValueError("unsupported count")
    chosen = {}
    for mode in modes:
        items = [x for x in trials if x["distribution"] == mode]
        if sorted(x["seed"] for x in items) != CALIBRATION_SEEDS:
            raise ValueError(f"calibration seeds missing: {n}/{mode}")
        calibrated = {}
        for j, size in enumerate(CANDIDATES):
            # Recall is printed with six decimals; reconstruct integer
            # hit counts over 12 independent queries * top5.
            hits = sum(round(item["options"][j]["recall_at_5"] * QUERIES * TOPK)
                       for item in items)
            calibrated[str(size)] = hits / (len(items) * QUERIES * TOPK)
        selected = next((size for size in CANDIDATES
                         if calibrated[str(size)] >= TARGET), None)
        if selected is None:
            selected = CANDIDATES[-1]
        chosen[mode] = {"selected_m": selected,
                        "calibration_recall_by_m": calibrated}
    return chosen


def validate_trial(r, n, mode, seed):
    if (r.get("kind") != "synthetic_cpu_int8_direct_shortlist_float32_rerank"
            or r.get("status") != "PASS" or r.get("sanity_failures") != 0
            or r.get("seed") != seed or r.get("distribution") != mode
            or (r.get("vectors"), r.get("dimensions"),
                r.get("queries"), r.get("repeats"), r.get("top_k"))
            != (n, 768, QUERIES, REPEATS, TOPK)
            or [x.get("candidates") for x in r.get("options", [])] != CANDIDATES):
        raise ValueError(f"incorrect trial: {n}/{mode}/{seed}")
    for i, opt in enumerate(r["options"]):
        if (not 0 <= opt["recall_at_5"] <= 1 or
                opt["end_to_end_p50_ms"] <= 0 or
                opt["int8_scan_p50_ms"] <= 0 or
                opt["rerank_only_p50_ms"] <= 0):
            raise ValueError("invalid benchmark metrics")
        if i and opt["recall_at_5"] + 1e-6 < r["options"][i-1]["recall_at_5"]:
            raise ValueError("recall not monotonic")


def run(binary, n, modes, seeds, chosen):
    data = []
    for mode in modes:
        selected = chosen[mode]["selected_m"]
        for seed in seeds:
            command = [str(binary), str(n), "768", str(QUERIES),
                       str(REPEATS), str(seed), mode]
            process = subprocess.run(command, capture_output=True,
                                     text=True, timeout=60, check=True)
            item = json.loads(process.stdout)
            validate_trial(item, n, mode, seed)
            options = [{
                "m": option["candidates"],
                "recall_at_5": option["recall_at_5"],
                "direct_p50_ms": option["end_to_end_p50_ms"],
                "int8_scan_p50_ms": option["int8_scan_p50_ms"],
                "float32_rerank_p50_ms": option["rerank_only_p50_ms"]
            } for option in item["options"]]
            selected_opt = next(o for o in options if o["m"] == selected)
            data.append({
                "seed": seed, "mode": mode, "vectors": n,
                "float32_exact_p50_ms": item["exact_float32_p50_ms"],
                "one_time_quantize_ms": item["quantize_vectors_and_queries_ms"],
                "selected_m_precommitted": selected,
                "selected_recall_at_5": selected_opt["recall_at_5"],
                "selected_direct_p50_ms": selected_opt["direct_p50_ms"],
                "options": options,
            })
            print(f"PASS n={n} mode={mode} seed={seed} M={selected} "
                  f"recall={selected_opt['recall_at_5']:.6f} "
                  f"direct_ms={selected_opt['direct_p50_ms']:.4f}", flush=True)
    return data


def summarize(rows, policy):
    answer = {}
    for mode, fit in policy.items():
        subset = [x for x in rows if x["mode"] == mode]
        if not subset:
            raise ValueError(f"no holdout for {mode}")
        m = fit["selected_m"]
        hits = sum(round(x["selected_recall_at_5"] * QUERIES * TOPK)
                   for x in subset)
        total = len(subset) * QUERIES * TOPK
        scores = [x["selected_recall_at_5"] for x in subset]
        base = statistics.median(x["float32_exact_p50_ms"] for x in subset)
        selected = statistics.median(x["selected_direct_p50_ms"] for x in subset)
        setup = statistics.median(x["one_time_quantize_ms"] for x in subset)
        # Nominal break-even assumes once-only vector preparation and
        # steady-state latency difference for comparable future queries.
        savings = base - selected
        break_even = math.ceil(setup / savings) if savings > 0 else None
        per_m = {}
        for i, option in enumerate(CANDIDATES):
            observations = [x["options"][i] for x in subset]
            hit_count = sum(round(v["recall_at_5"] * QUERIES * TOPK)
                            for v in observations)
            per_m[str(option)] = {
                "micro_recall_at_5": round(hit_count / total, 6),
                "median_direct_p50_ms": round(statistics.median(
                    v["direct_p50_ms"] for v in observations), 6),
            }
        answer[mode] = {
            "calibrated_m": m,
            "calibration_recall_at_m": fit["calibration_recall_by_m"][str(m)],
            "holdout_cases": len(subset),
            "holdout_recall_at_5": round(hits / total, 6),
            "holdout_hits": hits, "holdout_opportunities": total,
            "passes_target_99_percent": hits / total >= TARGET,
            "min_per_seed_recall": min(scores),
            "median_exact_float32_p50_ms": round(base, 6),
            "median_direct_policy_p50_ms": round(selected, 6),
            "nominal_median_speedup": round(base / selected, 4),
            "median_one_time_quantize_ms": round(setup, 6),
            "nominal_query_break_even_for_quantization": break_even,
            "all_m_holdout": per_m,
        }
    return answer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--c-source", type=Path, required=True)
    ap.add_argument("--small-calibration", type=Path, required=True)
    ap.add_argument("--large-calibration", type=Path, required=True)
    ap.add_argument("--small-seeds", type=int, default=20)
    ap.add_argument("--large-seeds", type=int, default=10)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.small_seeds < 1 or args.large_seeds < 1 or args.small_seeds > 100 or args.large_seeds > 100:
        ap.error("seed counts must be 1..100")
    if digest(args.c_source) != SOURCE_SHA:
        raise ValueError("C source SHA-256 mismatch")
    designs = [
        (8192, ["independent", "temporal", "clustered"],
         args.small_calibration, args.small_seeds),
        (32768, ["independent", "clustered"],
         args.large_calibration, args.large_seeds),
    ]
    fit = {}
    for n, modes, file, count in designs:
        fit[str(n)] = {
            "calibration_file_sha256": digest(file),
            "policy": calibration_policy(file, n, modes),
            "holdout_seeds": list(range(HOLDOUT_SEED_START,
                                        HOLDOUT_SEED_START + count)),
        }
        print(f"FROZEN policy n={n}: "
              f"{ {mode: p['selected_m'] for mode,p in fit[str(n)]['policy'].items()} }",
              flush=True)
    records = {}
    for n, modes, file, count in designs:
        conf = fit[str(n)]
        records[str(n)] = run(args.binary, n, modes,
                              conf["holdout_seeds"], conf["policy"])
    report = {
        "schema_version": 1,
        "kind": "synthetic_cpu_frozen_calibration_holdout",
        "date": "2026-10-29",
        "c_source_sha256": SOURCE_SHA,
        "calibration_seeds": CALIBRATION_SEEDS,
        "target_average_recall": TARGET,
        "policy_fit": fit,
        "results": records,
        "summary": {
            key: summarize(records[key], fit[key]["policy"])
            for key in records
        },
        "limitations": [
            "Synthetic deterministic distributions, not real embeddings",
            "Held-out seeds are disjoint from calibration seeds but generated by the same synthetic simulator",
            "Aggregate recall uses top-five hits as denominators; queries are not statistically independent ground-truth media",
            "End-to-end query timing includes int8 scan and float32 rerank but excludes setup, embedding, persistence, network, ANN index and GPU",
            "Nominal break-even is descriptive, not an observed throughput experiment",
            "Fixed policy uses known synthetic distribution label, not an inferred per-query classifier",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "result_file": str(args.output),
        "small_runs": len(records["8192"]),
        "large_runs": len(records["32768"]),
        "summary": report["summary"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
