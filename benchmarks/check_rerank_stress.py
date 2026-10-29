#!/usr/bin/env python3
"""Verify clustered/temporally-correlated synthetic CPU reranking receipts."""
import argparse
import json
import statistics
from pathlib import Path

SOURCE = "9ab57c8be2869271e22ae75b5878b55d67b89f14491eedd5aebbf5226e0bf0b9"
SEEDS = [20261029, 20261030, 20261031, 20261032, 20261033]
MODES = ["temporal", "clustered"]
K = [5, 10, 20, 40, 80, 160]

def validate(doc):
    if doc.get("kind") != "synthetic_correlated_and_clustered_rerank_multihost":
        raise ValueError("Wrong study kind")
    if doc.get("source_sha256") != SOURCE or doc.get("seeds") != SEEDS or doc.get("modes") != MODES:
        raise ValueError("Source/seed/distribution mismatch")
    hosts = doc.get("hosts", [])
    if len(hosts) != 3 or len({h["node"] for h in hosts}) != 3:
        raise ValueError("Expected three unique hosts")
    first = None
    for host in hosts:
        trials = host.get("trials", [])
        if len(trials) != 10:
            raise ValueError("Ten mode/seed trials required per host")
        lookup = {(x.get("distribution"),x.get("seed")):x for x in trials}
        if len(lookup) != 10:
            raise ValueError("Duplicate runs")
        signatures = {}
        for mode in MODES:
            for seed in SEEDS:
                x = lookup.get((mode,seed))
                if not x or x.get("status") != "PASS" or x.get("sanity_failures") != 0:
                    raise ValueError("Missing/failed trial")
                if (x.get("vectors"), x.get("dimensions"), x.get("queries"), x.get("repeats")) != (8192,768,12,2):
                    raise ValueError("Workload mismatch")
                opts = x.get("options", [])
                if [o["candidates"] for o in opts] != K:
                    raise ValueError("Candidate mismatch")
                recalls=[o["recall_at_5"] for o in opts]
                if any(not 0 <= v <= 1 for v in recalls):
                    raise ValueError("Recall out of range")
                if any(recalls[i] > recalls[i+1] + 1e-6 for i in range(len(recalls)-1)):
                    raise ValueError("Rerank recall must be nondecreasing")
                signatures[f"{mode}:{seed}"] = recalls
        if first is None:
            first = signatures
        elif signatures != first:
            raise ValueError("Recall differs across hosts for same seed and mode")
    by_mode = {}
    for mode in MODES:
        by_mode[mode] = {str(k):round(statistics.mean(first[f"{mode}:{seed}"][j] for seed in SEEDS),6) for j,k in enumerate(K)}
    return {"status":"PASS","hosts":len(hosts),"runs":sum(len(h["trials"]) for h in hosts),
            "independent_datasets":len(SEEDS)*len(MODES),"mean_recall":by_mode,
            "caveat":"Modes and seed datasets are synthetic, not independent real-world samples; the same cases are replayed on each host."}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("path",nargs="?",type=Path,default=Path(__file__).parent/"results"/"2026-10-29-rerank-stress-multiseed.json")
    args=parser.parse_args()
    print(json.dumps(validate(json.loads(args.path.read_text())),indent=2))
