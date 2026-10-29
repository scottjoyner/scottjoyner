#!/usr/bin/env python3
"""Validate that a published synthetic shortlist policy did not use holdout seeds.

No model or inference server is loaded. All recorded results must have valid
provenance, disjoint seeds, consistent options, and independently recomputed
summary metrics.
"""
import argparse
import json
import math
import statistics
from pathlib import Path

from bench_holdout import calibration_policy

SOURCE_SHA = "6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec"
CANDIDATES = [5, 10, 20, 40, 80, 160]
CALIB = [20261029, 20261030, 20261031, 20261032, 20261033]
SPECS = {"8192": (["independent", "temporal", "clustered"], 20),
         "32768": (["independent", "clustered"], 10)}
TOLERANCE = 0.00002


def near(a, b, tolerance=TOLERANCE):
    return abs(a-b) <= tolerance


def validate(doc):
    if doc.get("kind") != "synthetic_cpu_frozen_calibration_holdout" or doc.get("schema_version") != 1:
        raise ValueError("Wrong artifact type")
    if doc.get("c_source_sha256") != SOURCE_SHA or doc.get("calibration_seeds") != CALIB:
        raise ValueError("Source/seed provenance mismatch")
    if not near(doc.get("target_average_recall", -1), 0.99):
        raise ValueError("Unexpected preset recall target")
    if set(doc.get("results", {})) != set(SPECS) or set(doc.get("summary", {})) != set(SPECS):
        raise ValueError("Missing dataset sizes")
    if set(doc.get("policy_fit", {})) != set(SPECS):
        raise ValueError("Policy fit incomplete")
    # Re-fit from the already published calibration evidence. This detects
    # invented calibration metrics or a retroactively altered selection.
    directory = Path(__file__).parent / "results"
    calibration_paths = {
        "8192": directory / "2026-10-29-rerank-direct-multihost.json",
        "32768": directory / "2026-10-29-rerank-direct-32768-x1-370.json",
    }
    for count, (modes, _) in SPECS.items():
        independently_fitted = calibration_policy(calibration_paths[count],
                                                  int(count), modes)
        declared_fit = doc["policy_fit"][count]["policy"]
        if set(declared_fit) != set(independently_fitted):
            raise ValueError("Published calibration policy has wrong modes")
        for mode in modes:
            if (declared_fit[mode]["selected_m"] != independently_fitted[mode]["selected_m"] or
                any(not near(declared_fit[mode]["calibration_recall_by_m"][str(m)],
                             independently_fitted[mode]["calibration_recall_by_m"][str(m)], 1e-6)
                    for m in CANDIDATES)):
                raise ValueError(f"Published policy does not match primary calibration: {count}/{mode}")
    checks = 0
    results = {}
    for n, (modes, count) in SPECS.items():
        fit = doc["policy_fit"][n]
        expected_seeds = list(range(20261034, 20261034 + count))
        if fit.get("holdout_seeds") != expected_seeds:
            raise ValueError(f"Holdout seed range not frozen for {n}")
        if set(expected_seeds) & set(CALIB):
            raise ValueError("Holdout data leaked into calibration")
        if set(fit["policy"]) != set(modes):
            raise ValueError("Missing mode policy")
        trials = doc["results"][n]
        if len(trials) != len(modes) * count:
            raise ValueError(f"Missing held-out trials for {n}")
        seen = set()
        for item in trials:
            mode, seed = item.get("mode"), item.get("seed")
            if mode not in modes or seed not in expected_seeds or (mode, seed) in seen:
                raise ValueError("Unexpected or repeated seed/mode")
            seen.add((mode, seed))
            if item.get("vectors") != int(n) or item.get("float32_exact_p50_ms", 0) <= 0:
                raise ValueError("Invalid experiment configuration")
            if item.get("one_time_quantize_ms", 0) <= 0:
                raise ValueError("Invalid preparation time")
            options = item.get("options", [])
            if [o.get("m") for o in options] != CANDIDATES:
                raise ValueError("Incomplete candidate sweep")
            vals = [o.get("recall_at_5", -1) for o in options]
            if any(not 0 <= r <= 1 for r in vals):
                raise ValueError("Invalid recall metric")
            if any(vals[i] > vals[i+1] + 1e-6 for i in range(5)):
                raise ValueError("Recall declined as shortlist grew")
            if any(o.get("direct_p50_ms", 0) <= 0 or o.get("int8_scan_p50_ms", 0) <= 0 or
                   o.get("float32_rerank_p50_ms", 0) <= 0 for o in options):
                raise ValueError("Invalid latency")
            selected = fit["policy"][mode]["selected_m"]
            if selected not in CANDIDATES or item.get("selected_m_precommitted") != selected:
                raise ValueError("Changed shortlist after holdout")
            selected_row = options[CANDIDATES.index(selected)]
            if not near(selected_row["recall_at_5"], item["selected_recall_at_5"], 1e-6) or not near(
                    selected_row["direct_p50_ms"], item["selected_direct_p50_ms"], 1e-6):
                raise ValueError("Selected metrics not drawn from frozen option")
            checks += 1
        if len(seen) != len(modes) * count:
            raise ValueError("Missing combinations")
        mode_out = {}
        for mode in modes:
            fit_mode = fit["policy"][mode]
            calibration = fit_mode["calibration_recall_by_m"]
            if set(calibration) != set(map(str, CANDIDATES)):
                raise ValueError("Incomplete calibration")
            expected_selection = next((m for m in CANDIDATES if calibration[str(m)] >= .99), 160)
            if fit_mode["selected_m"] != expected_selection:
                raise ValueError("Selection not fitted solely from calibration")
            selected = fit_mode["selected_m"]
            subset = [t for t in trials if t["mode"] == mode]
            observed = doc["summary"][n][mode]
            hit_count = sum(round(r["selected_recall_at_5"]*12*5) for r in subset)
            recall = hit_count/(count*12*5)
            if (observed["holdout_hits"] != hit_count or
                    observed["holdout_opportunities"] != count*12*5 or
                    not near(observed["holdout_recall_at_5"], recall) or
                    observed["passes_target_99_percent"] != (recall >= .99) or
                    observed["calibrated_m"] != selected):
                raise ValueError("Published holdout summary mismatches raw evidence")
            exact_ms = statistics.median(x["float32_exact_p50_ms"] for x in subset)
            policy_ms = statistics.median(x["selected_direct_p50_ms"] for x in subset)
            q_ms = statistics.median(x["one_time_quantize_ms"] for x in subset)
            if not near(observed["median_exact_float32_p50_ms"], exact_ms) or not near(
                    observed["median_direct_policy_p50_ms"], policy_ms) or not near(
                    observed["median_one_time_quantize_ms"], q_ms):
                raise ValueError("Reported median timing mismatch")
            for idx, m in enumerate(CANDIDATES):
                hit_count_m = sum(round(x["options"][idx]["recall_at_5"]*12*5) for x in subset)
                rec_m = hit_count_m/(count*12*5)
                mmedian = statistics.median(x["options"][idx]["direct_p50_ms"] for x in subset)
                got = observed["all_m_holdout"][str(m)]
                if not near(got["micro_recall_at_5"], rec_m) or not near(
                        got["median_direct_p50_ms"], mmedian):
                    raise ValueError(f"Incorrect {n}/{mode}/M{m} summary")
            mode_out[mode] = {
                "calibrated_m": selected, "holdout_recall_at_5": round(recall, 6),
                "meets_99_percent_target": recall >= .99,
                "median_policy_latency_ms": round(policy_ms, 6),
                "median_exact_latency_ms": round(exact_ms, 6),
                "quantization_ms": round(q_ms, 6),
            }
        results[n] = mode_out
    return {
        "status": "PASS", "validated_holdout_trials": checks,
        "policy_fitted_on_disjoint_5_seed_calibration": True,
        "sizes": results,
        "limits": "Synthetic CPU-only, query precision not statistically independent; no real media or GPU",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path, nargs="?",
                    default=Path(__file__).parent/"results"/"2026-10-29-holdout-frozen-policy.json")
    args = ap.parse_args()
    print(json.dumps(validate(json.loads(args.path.read_text(encoding="utf-8"))), indent=2))
