#!/usr/bin/env python3
"""Recompute score-gap calibration and disjoint holdout accuracy from raw traces.

The score-margin policy uses quantized scores only. Oracle hits are checked
only AFTER its decisions, which are audited for non-leakage.
"""
import argparse
import json
import math
import statistics
from pathlib import Path

SOURCE = "ce4fa7173f7237fcdc5460671c9d8643685679bec4f0547dfe3b039bb95ffac0"
CAL_SEEDS = list(range(20261029,20261034))
EVAL_SEEDS = list(range(20261100,20261116))
MODES={8192:["independent","temporal","clustered"],32768:["independent","clustered"]}
CAND=[5,10,20,40,80,160]
POLICY=[20,40,80,160]
EXPECTED_THRESHOLD=.0064
TOL=1e-5

def choose(q,t):
    return next((m for m in POLICY[:3]
                 if q[f"gap{m}"]>=t),160)

def calibration_stats(runs,t):
    by_group={}
    for run in runs:
        label=f'{run["n"]}/{run["distribution"]}'
        stats=by_group.setdefault(label,[0,0,0,0])
        for q in run["query_details"]:
            m=choose(q,t)
            stats[0]+=q["hits_by_m"][CAND.index(m)]
            stats[1]+=5
            stats[2]+=m
            stats[3]+=1
    hits=sum(x[0]for x in by_group.values())
    total=sum(x[1]for x in by_group.values())
    min_quality=min(x[0]/x[1]for x in by_group.values())
    mean_m=sum(x[2]for x in by_group.values())/sum(x[3]for x in by_group.values())
    return hits/total,min_quality,mean_m

def validate(cal,hold):
    if cal.get("source_sha256")!=SOURCE or hold.get("source_sha256")!=SOURCE:
        raise ValueError("C source mismatch")
    if cal.get("kind")!="synthetic_query_score_margin_threshold_calibration" or \
       hold.get("kind")!="synthetic_query_score_margin_disjoint_holdout":
        raise ValueError("Wrong artifact types")
    if cal.get("calibration_seed_values")!=CAL_SEEDS or \
       hold.get("calibration_seed_values")!=CAL_SEEDS or \
       hold.get("holdout_seed_values")!=EVAL_SEEDS:
        raise ValueError("Incorrect or overlapping seed split")
    if len(cal.get("raw_runs",[]))!=25 or len(hold.get("runs",[]))!=80:
        raise ValueError("Run count mismatch")
    if sum(len(r["query_details"])for r in cal["raw_runs"])!=300:
        raise ValueError("Calibration case count wrong")
    best=None
    for index in range(101):
        t=index/10000
        rec,worst,m_mean=calibration_stats(cal["raw_runs"],t)
        if rec>=.995 and worst>=.99:
            item=(m_mean,-worst,t,rec)
            if best is None or item<best:
                best=item
    if best is None or not math.isclose(best[2],EXPECTED_THRESHOLD,abs_tol=1e-9):
        raise ValueError(f"Calibration cannot reproduce preset threshold: {best}")
    if cal["selected"]["threshold"]!=best[2] or \
       abs(cal["selected"]["mean_m"]-best[0])>TOL:
        raise ValueError("Saved calibration selection differs from raw oracle")
    if hold.get("margin_threshold_fixed_pre_holdout")!=best[2]:
        raise ValueError("Holdout changed frozen threshold")
    checks=0
    group_outputs={}
    for n,modes in MODES.items():
        for mode in modes:
            cases=[r for r in hold["runs"] if r["n"]==n and r["distribution"]==mode]
            if len(cases)!=len(EVAL_SEEDS) or sorted(x["seed"]for x in cases)!=EVAL_SEEDS:
                raise ValueError(f"Missing holdout cases {n}/{mode}")
            all_queries=[]
            for r in cases:
                if (r.get("status")!="PASS" or r.get("sanity_failures")!=0 or
                    (r["d"],r["queries"],r["repeats"])!=(768,12,2) or
                    not math.isclose(r["threshold"],best[2],abs_tol=1e-9) or
                    len(r["query_details"])!=12):
                    raise ValueError("Trial correctness failure")
                hits=0
                for q in r["query_details"]:
                    if q["selected_m"]!=choose(q,best[2]):
                        raise ValueError("Oracle or distribution leakage into selection")
                    m=q["selected_m"]
                    if q["hits_by_m"][CAND.index(m)]!=q["hits_selected"] or \
                       q["hits_by_m"][5]!=q["hits_160"]:
                        raise ValueError("Incorrect rerank evidence")
                    if not 0<=q["hits_selected"]<=5 or \
                       q["query_ms"]<=0 or q["exact_ms"]<=0:
                        raise ValueError("Invalid query numbers")
                    hits+=q["hits_selected"]
                    all_queries.append(q)
                    checks+=1
                if abs(hits/60-r["adaptive_recall_at5"])>2e-7:
                    raise ValueError("Run recall inaccurate")
            x=hold["summary"][str(n)][mode]
            hits=sum(q["hits_selected"]for q in all_queries)
            total=len(all_queries)*5
            recall=hits/total
            meanm=sum(q["selected_m"]for q in all_queries)/len(all_queries)
            if (x["adaptive_hits"]!=hits or x["top5_opportunities"]!=total or
                abs(x["adaptive_recall_at5"]-recall)>2e-6 or
                abs(x["mean_chosen_m"]-meanm)>0.001 or
                x["passes_target_99pct"] != (recall>=.99)):
                raise ValueError(f"Published summary incorrect {n}/{mode}")
            for idx,m in enumerate(CAND):
                observed=sum(q["hits_by_m"][idx]for q in all_queries)/total
                if abs(x["fixed_m_recall_at5"][str(m)]-observed)>2e-6:
                    raise ValueError("Fixed-M comparator incorrect")
            group_outputs[f"{n}/{mode}"]={
                "recall":round(recall,6),
                "passes_99pct":recall>=.99,
                "mean_m":round(meanm,3),
                "fixed_160_recall":x["fixed_m_recall_at5"]["160"],
            }
    if checks!=960:
        raise ValueError("Wrong total query count")
    return {"status":"PASS","frozen_threshold":best[2],
            "calibration_query_cases":300,"heldout_query_cases":checks,
            "heldout_independent_datasets":80,
            "results":group_outputs,
            "limits":"Synthetic score-margin controller only; no real embedding distribution, GPU or ANN"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--calibration",type=Path,
                   default=Path(__file__).parent/"results"/"2026-10-29-score-margin-calibration.json")
    p.add_argument("--holdout",type=Path,
                   default=Path(__file__).parent/"results"/"2026-10-29-score-margin-holdout.json")
    a=p.parse_args()
    print(json.dumps(validate(json.loads(a.calibration.read_text()),
                              json.loads(a.holdout.read_text())),indent=2))
