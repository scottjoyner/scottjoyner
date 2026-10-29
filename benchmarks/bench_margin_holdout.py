#!/usr/bin/env python3
"""Query-only margin shortlist: frozen threshold, disjoint synthetic holdout.

Threshold and objective were published before evaluation. Selects a candidate
count using only int8 scores, NEVER distribution label or float32 oracle.
"""
import argparse
import hashlib
import json
import statistics
import subprocess
from pathlib import Path

SOURCE_SHA = "ce4fa7173f7237fcdc5460671c9d8643685679bec4f0547dfe3b039bb95ffac0"
CALIB_SEEDS = list(range(20261029,20261034))
EVAL_SEEDS = list(range(20261100,20261116))
MODES = {8192: ["independent","temporal","clustered"],
         32768: ["independent","clustered"]}
M_CHOICES = [20,40,80,160]

def choose(q, t):
    for m in M_CHOICES[:-1]:
        if q[f"gap{m}"] >= t:
            return m
    return 160

def collect(binary, source, calibration):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA or calibration["source_sha256"] != SOURCE_SHA:
        raise ValueError("Wrong pinned C source")
    if calibration["calibration_seed_values"] != CALIB_SEEDS or \
       calibration["n_calibration_runs"] != 25 or \
       calibration["n_query_cases"] != 300:
        raise ValueError("Calibration provenance mismatch")
    t = calibration["selected"]["threshold"]
    if t != 0.0064:
        raise ValueError("Unexpected uncommitted margin threshold")
    all_runs = []
    for n,modes in MODES.items():
        for mode in modes:
            for seed in EVAL_SEEDS:
                command = [str(binary),str(n),"768","12","2",str(seed),mode,str(t)]
                p = subprocess.run(command,capture_output=True,text=True,
                                   check=True,timeout=65)
                x = json.loads(p.stdout)
                if (x.get("status")!="PASS" or x.get("sanity_failures")!=0 or
                    (x["n"],x["d"],x["seed"],x["distribution"])!=(n,768,seed,mode) or
                    len(x.get("query_details",[]))!=12 or abs(x["threshold"]-t)>1e-9):
                    raise ValueError("Invalid trial")
                hits=0
                for q in x["query_details"]:
                    m=choose(q,t)
                    if m!=q["selected_m"]:
                        raise ValueError("Decision depended on something other than quantized score margins")
                    if len(q.get("hits_by_m",[]))!=6 or any(not 0<=v<=5 for v in q["hits_by_m"]):
                        raise ValueError("Wrong diagnostic accuracy")
                    if q["hits_by_m"][[5,10,20,40,80,160].index(m)] != q["hits_selected"]:
                        raise ValueError("Accuracy mismatch")
                    hits+=q["hits_selected"]
                if abs(x["adaptive_recall_at5"]-hits/(12*5))>0.000001:
                    raise ValueError("Aggregate recall mismatch")
                all_runs.append(x)
                print(f"PASS n={n} mode={mode} seed={seed} "
                      f"recall={x['adaptive_recall_at5']:.4f} "
                      f"median_ms={x['adaptive_median_direct_ms']:.4f}",flush=True)
    summary = {}
    for n,modes in MODES.items():
        summary[str(n)] = {}
        for mode in modes:
            rows=[r for r in all_runs if r["n"]==n and r["distribution"]==mode]
            queries=[q for r in rows for q in r["query_details"]]
            t_hits=sum(q["hits_selected"] for q in queries)
            opp=len(queries)*5
            fixed={}
            for i,m in enumerate([5,10,20,40,80,160]):
                fixed[str(m)] = round(sum(q["hits_by_m"][i] for q in queries)/opp,6)
            hist={str(m):sum(q["selected_m"]==m for q in queries) for m in M_CHOICES}
            direct=statistics.median(r["adaptive_median_direct_ms"] for r in rows)
            baseline=statistics.median(r["exact_median_ms"] for r in rows)
            summary[str(n)][mode]={
                "holdout_runs":len(rows),"query_cases":len(queries),
                "adaptive_hits":t_hits,"top5_opportunities":opp,
                "adaptive_recall_at5":round(t_hits/opp,6),
                "passes_target_99pct":t_hits/opp>=.99,
                "fixed_m_recall_at5":fixed,
                "chosen_m_histogram":hist,
                "mean_chosen_m":round(sum(q["selected_m"] for q in queries)/len(queries),3),
                "median_adaptive_direct_query_ms":round(direct,6),
                "median_exact_query_ms":round(baseline,6),
                "nominal_query_speedup_x":round(baseline/direct,4),
                "median_one_time_quantize_ms":round(statistics.median(r["prequantize_ms"]for r in rows),6),
                "top160_recall_at5":round(sum(q["hits_160"] for q in queries)/opp,6),
            }
    return {
        "schema_version":1,"kind":"synthetic_query_score_margin_disjoint_holdout",
        "date":"2026-10-29","source_sha256":SOURCE_SHA,
        "source_commit":"5d723b513186601ce1b0d0cc25c136da08db81da",
        "margin_threshold_fixed_pre_holdout":t,
        "calibration_sha256":hashlib.sha256(json.dumps(calibration,sort_keys=True).encode()).hexdigest(),
        "calibration_seed_values":CALIB_SEEDS,"holdout_seed_values":EVAL_SEEDS,
        "strategy":"One quantized top160 scan; choose M=20,40,80 based solely on score5-scoreM >= threshold, else M=160. Then rescore topM in float32.",
        "dataset_generator_modes":MODES,"runs":all_runs,"summary":summary,
        "limitations":[
            "Synthetic CPU brute-force scans, not real dashcam/trace embeddings",
            "Known simulation modes generate data but never determine a query's shortlist size",
            "Calibration and held-out seeds are disjoint yet share the same simulation generator",
            "Exact float32 oracle is used for diagnostics after prediction, never decision-making",
            "One initial top160 scan is performed regardless of selected M; potential speed benefit limited to float32 reranking",
            "Search excludes embedding generation, quantization and persistence; prequantization measured separately",
            "Aggregate top-five hit counts are descriptive, not a confidence guarantee",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--binary",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--calibration",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    c=json.loads(a.calibration.read_text())
    result=collect(a.binary,a.source,c)
    a.out.write_text(json.dumps(result,separators=(",",":"))+"\n")
    print(json.dumps({"status":"PASS","total_runs":len(result["runs"]),
                      "summary":result["summary"]},indent=2),flush=True)

if __name__=="__main__":
    main()
