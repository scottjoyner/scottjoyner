#!/usr/bin/env python3
"""Summarize immutable synthetic CPU results; do not infer GPU/DB performance."""
import argparse
import json
from pathlib import Path

PYTHON_SOURCE_SHA = "21cceec9904967d6a41c652f69752ca0e793adec9a6f6d8500930c63984914cc"
C_SOURCE_SHA = "e443f9e8d794f53f11fe1b3f66dfd5b7013e98a14d3d00dac601691ef7a60aea"
C_COMMIT = "1fbfc9d1a343890cc525708379d101da7ba0730d"

def load_results(directory, date):
    python_runs = {}
    compiled_runs = []
    for path in sorted(directory.glob(date + "-*.json")):
        if "summary" in path.name:
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        kind = obj.get("benchmark_kind")
        if kind == "synthetic_python_cpu_not_production_data":
            if obj.get("status") != "PASS" or obj.get("source_sha256") != PYTHON_SOURCE_SHA:
                raise ValueError("Python evidence failed source/status validation: " + str(path))
            geo = next((r for r in obj.get("geo", []) if r.get("events") == 50000), None)
            vec = next((r for r in obj.get("vectors", []) if r.get("vectors") == 8192), None)
            if not geo or not vec or geo.get("mismatches") != 0:
                raise ValueError("Python workload missing or incorrect: " + str(path))
            if obj["host"] in python_runs:
                raise ValueError("Duplicate Python host: " + obj["host"])
            python_runs[obj["host"]] = {
                "file": str(path.name),
                "geo_50k_index_p50_ms": geo["indexed"]["p50_ms"],
                "geo_50k_linear_p50_ms": geo["baseline"]["p50_ms"],
                "geo_50k_mismatches": geo["mismatches"],
                "vector_8192_float64_p50_ms": vec["float64_exact_scan"]["p50_ms"],
                "vector_8192_int8_p50_ms": vec["int8_quantized_scan"]["p50_ms"],
                "vector_8192_int8_recall_at_5": vec["int8_recall_at_k_vs_float64"],
            }
        elif kind == "synthetic_compiled_cpu_vector_scan":
            if obj.get("status") != "PASS" or obj.get("sanity_failures") != 0:
                raise ValueError("Compiled evidence failed validation: " + str(path))
            a, b = obj["float32_p50_ms"], obj["int8_p50_ms"]
            if a <= 0 or b <= 0 or not 0 <= obj["int8_recall_at_5"] <= 1:
                raise ValueError("Invalid numerical evidence: " + str(path))
            compiled_runs.append({
                "file": str(path.name), "host": obj["host"],
                "compiler": obj["compiler"], "vectors": obj["vectors"],
                "dimensions": obj["dimensions"], "queries": obj["queries"],
                "repeats": obj["repeats"],
                "float32_p50_ms": a, "int8_p50_ms": b,
                "int8_speedup_x": round(a / b, 3),
                "int8_recall_at_5": obj["int8_recall_at_5"],
            })
    if not python_runs or not compiled_runs:
        raise ValueError("Both Python and compiled evidence are required")
    seen = set()
    for r in compiled_runs:
        key = (r["host"], r["vectors"], r["dimensions"])
        if key in seen:
            raise ValueError("Duplicate compiled workload: " + str(key))
        seen.add(key)
    return {
        "schema_version": 1,
        "date": date,
        "type": "synthetic_fleet_cpu_benchmark_summary",
        "provenance": {
            "python_source_sha256": PYTHON_SOURCE_SHA,
            "compiled_c_source_sha256": C_SOURCE_SHA,
            "compiled_c_source_commit": C_COMMIT,
            "compilation": "gcc -O3 -Wall -Wextra -std=c11 -lm (GCC 13 fallback on Raspberry Pi)",
        },
        "python_host_count": len(python_runs),
        "compiled_run_count": len(compiled_runs),
        "python_by_host": dict(sorted(python_runs.items())),
        "compiled_runs": sorted(compiled_runs, key=lambda x: (x["vectors"], x["host"])),
        "limitations": [
            "Synthetic deterministic workloads, not production data or Neo4j.",
            "CPU-only; no GPU, NPU, ROCm or MLX inference was measured.",
            "Float32 and int8 metrics refer to compiled brute-force scan, not indexed ANN.",
            "Cold/warm system load, compiler differences and architecture affect timing.",
            "Recall is a function of the common synthetic seed and should not be generalized.",
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--date", default="2026-10-29")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = load_results(args.directory, args.date)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
