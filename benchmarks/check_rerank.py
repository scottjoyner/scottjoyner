#!/usr/bin/env python3
"""Validate synthetic CPU shortlist/rerank benchmark receipts without external packages."""
import argparse
import json
import statistics
from pathlib import Path

HASH = "5645714c28be20326736cce25e446ea003fa9b00d7989891a0b6f0cefd4609b1"
SEEDS = [20261029, 20261030, 20261031, 20261032, 20261033]
CANDIDATES = [5, 10, 20, 40, 80, 160]

def check(doc):
    if doc.get("kind") != "synthetic_int8_shortlist_float32_rerank_multihost":
        raise ValueError("Wrong kind")
    if doc.get("source_sha256") != HASH or doc.get("seed_values") != SEEDS:
        raise ValueError("Incorrect source hash or seeds")
    if doc.get("dataset_count") != 5:
        raise ValueError("Dataset count should count independent seeds")
    hosts = doc.get("hosts", [])
    if len(hosts) != 6 or len({h["node"] for h in hosts}) != 6:
        raise ValueError("Expected six distinct hosts")
    truth = None
    for h in hosts:
        trials = h.get("trials", [])
        if [t.get("seed") for t in trials] != SEEDS:
            raise ValueError("Missing or wrong seed order on " + h["node"])
        values = []
        for t in trials:
            if t.get("status") != "PASS" or t.get("sanity_failures") != 0:
                raise ValueError("A run failed")
            if (t.get("vectors"),t.get("dimensions"),t.get("queries"),t.get("repeats"),t.get("top_k")) != (8192,768,12,2,5):
                raise ValueError("Workload mismatch")
            opts = t.get("options", [])
            if [o["candidates"] for o in opts] != CANDIDATES:
                raise ValueError("Option mismatch")
            recalls = [o["recall_at_5"] for o in opts]
            if any(x < 0 or x > 1 for x in recalls):
                raise ValueError("Invalid recall")
            if any(recalls[i] > recalls[i+1] + 1e-6 for i in range(len(recalls)-1)):
                raise ValueError("Recall must not decline as candidate set grows")
            if any(o["rerank_only_p50_ms"] <= 0 or o["approx_plus_rerank_p50_ms_estimate"] <= 0 for o in opts):
                raise ValueError("Invalid timings")
            values.append(recalls)
        if truth is None:
            truth = values
        elif truth != values:
            raise ValueError("Identical seeds produced different recall on separate hosts")
    mean_by_candidates = {
        str(c): round(statistics.mean(truth[i][j] for i in range(len(SEEDS))),6)
        for j,c in enumerate(CANDIDATES)
    }
    return {
        "status":"PASS",
        "hosts":len(hosts),
        "total_runs":sum(len(h["trials"]) for h in hosts),
        "independent_datasets":len(SEEDS),
        "mean_recall_by_candidates":mean_by_candidates,
        "minimum_candidates_reaching_perfect_recall_on_these_seeds":
            next((c for j,c in enumerate(CANDIDATES) if all(truth[i][j] >= 1 for i in range(len(SEEDS))), None),
        "interpretation":"No guarantees about unseen or non-Gaussian embeddings. Timing component-sums are estimates, not directly measured end-to-end p50.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("file",nargs="?",type=Path,default=Path(__file__).parent/"results"/"2026-10-29-rerank-multiseed.json")
    args=ap.parse_args()
    print(json.dumps(check(json.loads(args.file.read_text())),indent=2))

if __name__=="__main__":
    main()
