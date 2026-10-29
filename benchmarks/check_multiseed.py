#!/usr/bin/env python3
"""Validate and summarize 768D synthetic multi-seed CPU evidence (stdlib only)."""
import argparse
import json
import statistics
from pathlib import Path

EXPECTED_C_SOURCE_SHA = "439281cc5c46379571596437dc96f9aebc5e6b0ffd85be163a457e7c779caa73"
EXPECTED_SEEDS = [20261029, 20261030, 20261031, 20261032, 20261033]


def validate_results(report):
    if report.get("benchmark_kind") != "synthetic_compiled_cpu_multiseed_768d":
        raise ValueError("Unexpected dataset type")
    if report.get("source_sha256") != EXPECTED_C_SOURCE_SHA:
        raise ValueError("Source integrity mismatch")
    if report.get("seeds") != EXPECTED_SEEDS:
        raise ValueError("Seed set mismatch")
    if (report.get("vectors"), report.get("dimensions"), report.get("queries"),
            report.get("repeats")) != (8192, 768, 12, 2):
        raise ValueError("Workload mismatch")
    nodes = report.get("run_nodes", [])
    if len(nodes) != 6 or len({node["node"] for node in nodes}) != 6:
        raise ValueError("Expected six unique Linux host runs")
    baseline_recalls = None
    summary = []
    for node in nodes:
        samples = node.get("trials", [])
        if len(samples) != len(EXPECTED_SEEDS):
            raise ValueError("Missing seed trial on " + node["node"])
        seeds = [r.get("seed") for r in samples]
        if seeds != EXPECTED_SEEDS:
            raise ValueError("Wrong seed order on " + node["node"])
        for item in samples:
            if item.get("status") != "PASS" or item.get("sanity_failures") != 0:
                raise ValueError("Correctness failure on " + node["node"])
            if item.get("dimensions") != 768 or item.get("vectors") != 8192:
                raise ValueError("Unexpected vectors/dimensions on " + node["node"])
            if not 0 <= item.get("int8_recall_at_5", -1) <= 1:
                raise ValueError("Invalid recall")
            if item.get("float32_p50_ms", 0) <= 0 or item.get("int8_p50_ms", 0) <= 0:
                raise ValueError("Invalid latency")
        recalls = [r["int8_recall_at_5"] for r in samples]
        if baseline_recalls is None:
            baseline_recalls = recalls
        elif recalls != baseline_recalls:
            raise ValueError("Deterministic recall differs across hosts")
        f = statistics.median(r["float32_p50_ms"] for r in samples)
        q = statistics.median(r["int8_p50_ms"] for r in samples)
        summary.append({
            "host": node["host"],
            "median_float32_p50_ms": round(f, 6),
            "median_int8_p50_ms": round(q, 6),
            "median_latency_ratio_x": round(f / q, 3),
        })
    return {
        "status": "PASS",
        "hosts": len(nodes),
        "compiled_runs": sum(len(n["trials"]) for n in nodes),
        "independent_seed_datasets": len(EXPECTED_SEEDS),
        "mean_recall_at_5": round(statistics.mean(baseline_recalls), 6),
        "min_recall_at_5": min(baseline_recalls),
        "max_recall_at_5": max(baseline_recalls),
        "seed_recalls": dict(zip(map(str, EXPECTED_SEEDS), baseline_recalls)),
        "hosts_summary": summary,
        "caveat": "Identical seeds on multiple hosts are reproducibility checks, not independent accuracy datasets.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", type=Path,
                    default=Path(__file__).parent / "results" / "2026-10-29-768d-multiseed.json")
    args = ap.parse_args()
    raw = json.loads(args.file.read_text(encoding="utf-8"))
    print(json.dumps(validate_results(raw), indent=2))


if __name__ == "__main__":
    main()
