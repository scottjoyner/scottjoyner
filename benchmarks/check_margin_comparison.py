#!/usr/bin/env python3
"""Validate matched adaptive-vs-fixed160 CPU timings and frozen decisions."""
import argparse
import json
import statistics
from pathlib import Path

SOURCE = "ce4fa7173f7237fcdc5460671c9d8643685679bec4f0547dfe3b039bb95ffac0"
WORKLOADS = [(8192,"independent"),(8192,"temporal"),(8192,"clustered"),
             (32768,"independent"),(32768,"clustered")]
SEEDS = list(range(20261100,20261108))
THRESHOLD = .0064

def validate(obj):
    if obj.get("kind") != "synthetic_query_adaptive_vs_fixed160_paired_cpu" or \
       obj.get("schema_version") != 1 or \
       obj.get("source_sha256") != SOURCE or \
       obj.get("threshold_frozen") != THRESHOLD or \
       obj.get("seeds") != SEEDS:
        raise ValueError("Provenance mismatch")
    rows=obj.get("results",[])
    if len(rows)!=len(WORKLOADS)*len(SEEDS):
        raise ValueError("Expected 40 A/B matched seed cases")
    seen=set()
    summary={}
    for n,mode in WORKLOADS:
        subset=[]
        for seed in SEEDS:
            match=[r for r in rows if (r.get("n"),r.get("mode"),r.get("seed"))==(n,mode,seed)]
            if len(match)!=1:
                raise ValueError("Duplicate or missing matched case")
            r=match[0]
            seen.add((n,mode,seed))
            adapt, fixed=r["adapt"],r["fixed160"]
            if r.get("order") not in (["adapt","fixed160"],["fixed160","adapt"]):
                raise ValueError("Unrecognized test order")
            if len(adapt["raw_m_choices"])!=12 or len(fixed["raw_m_choices"])!=12:
                raise ValueError("Missing choices")
            if any(m not in (20,40,80,160) for m in adapt["raw_m_choices"]):
                raise ValueError("Adaptive chose invalid shortlist")
            if any(m!=160 for m in fixed["raw_m_choices"]):
                raise ValueError("Fixed path chose non-160")
            if adapt["top5_hits"]>fixed["top5_hits"] or not 0<=fixed["top5_hits"]<=60:
                raise ValueError("Accuracy impossible")
            if adapt["median_ms"]<=0 or fixed["median_ms"]<=0:
                raise ValueError("Invalid timings")
            if abs(adapt["mean_M"]-statistics.mean(adapt["raw_m_choices"]))>1e-6:
                raise ValueError("Candidate mean mismatches raw choices")
            subset.append(r)
        recorded=obj["summary"][f"{n}/{mode}"]
        ratio=statistics.median(r["fixed160"]["median_ms"]/r["adapt"]["median_ms"]for r in subset)
        selected=statistics.median(r["adapt"]["median_ms"]for r in subset)
        baseline=statistics.median(r["fixed160"]["median_ms"]for r in subset)
        if not (abs(recorded["median_pairwise_fixed160_to_adaptive_ratio"]-ratio)<2e-6 and
                abs(recorded["adapt_median_ms"]-selected)<2e-6 and
                abs(recorded["fixed160_median_ms"]-baseline)<2e-6):
            raise ValueError("Published A/B timing summary doesn't match receipts")
        for label in ("adapt","fixed160"):
            if recorded[f"{'adaptive' if label=='adapt' else 'fixed160'}_hits"] != sum(
                    r[label]["top5_hits"]for r in subset):
                raise ValueError("Hit total mismatch")
        summary[f"{n}/{mode}"]={
            "median_pairwise_fixed160_to_adaptive_ratio":round(ratio,6),
            "adaptive_hits":sum(r["adapt"]["top5_hits"]for r in subset),
            "fixed160_hits":sum(r["fixed160"]["top5_hits"]for r in subset),
        }
    if len(seen)!=len(rows):
        raise ValueError("Unexpected trials")
    return {"status":"PASS","pairs":len(rows),"summary":summary,
            "scope":"Matched timing comparison on previously used synthetic seeds; not an independent accuracy holdout"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",nargs="?",type=Path,
                   default=Path(__file__).parent/"results"/"2026-10-29-score-margin-vs-fixed160.json")
    a=p.parse_args()
    print(json.dumps(validate(json.loads(a.path.read_text(encoding="utf-8"))),indent=2))
