#!/usr/bin/env python3
"""Validate fixed127 vs per-vector absmax quantization CPU benchmark receipts.

Recomputes all recall and timing aggregates from 60 recorded synthetic trials,
checks source fingerprint, metadata and exact-seed coverage. Uses stdlib only.
"""
import argparse
import json
import statistics
from pathlib import Path

SOURCE_SHA="b95bf19e86cc24f3c360eef782f0e357e6ec63bf61f4cd269070413d5f738e50"
SEEDS=list(range(20261120,20261130))
SIZES=[8192,32768]
MODES=["independent","temporal","clustered"]
CANDIDATES=[20,40,80,160]
SCHEMES=["fixed127","per_vector_absmax"]

def close(x,y,eps=1e-5):
    return abs(x-y)<=eps

def validate(doc):
    if doc.get("schema_version")!=1 or doc.get("kind")!="synthetic_cpu_quant_fixed127_vs_per_vector_absmax_holdout":
        raise ValueError("Wrong kind/schema")
    if doc.get("source_sha256")!=SOURCE_SHA:
        raise ValueError("C source hash differs")
    if (doc.get("seed_range"),doc.get("vector_counts"),doc.get("distribution_types"),
        doc.get("candidate_sizes"),doc.get("dimensions"),doc.get("queries"),doc.get("repeats")) != \
       (SEEDS,SIZES,MODES,CANDIDATES,768,12,2):
        raise ValueError("Benchmark configuration mismatch")
    runs=doc.get("runs",[])
    if len(runs)!=len(SEEDS)*len(SIZES)*len(MODES):
        raise ValueError("Wrong number of run receipts")
    by_key={(r["vectors"],r["distribution"],r["seed"]):r for r in runs}
    if len(by_key)!=len(runs):
        raise ValueError("Duplicate receipt")
    summaries={}
    for n in SIZES:
        summaries[str(n)]={}
        for mode in MODES:
            sample=[]
            for seed in SEEDS:
                r=by_key.get((n,mode,seed))
                if not r or (r.get("status")!="PASS" or r.get("sanity_failures")!=0 or
                    (r.get("dimensions"),r.get("queries"),r.get("repeats"))!=(768,12,2)):
                    raise ValueError("Missing or invalid seed trial")
                if r.get("float32_exact_p50_ms",0)<=0 or r.get("float32_exact_p95_ms",0)<=0:
                    raise ValueError("Invalid baseline")
                schemes=r.get("schemes",[])
                if [s.get("name")for s in schemes]!=SCHEMES:
                    raise ValueError("Quantization scheme labels mismatched")
                for s in schemes:
                    if (s.get("raw_vector_bytes"),s.get("scale_metadata_bytes"))!=(n*768,n*4):
                        raise ValueError("Storage information inaccurate")
                    if s.get("quantize_precompute_ms",0)<=0:
                        raise ValueError("Invalid preprocessing time")
                    options=s.get("topk_results",[])
                    if [o.get("candidates")for o in options]!=CANDIDATES:
                        raise ValueError("Missing shortlist sizes")
                    prev=0
                    for v in options:
                        hits=v.get("hits",-1)
                        if hits!=round(hits) or not 0<=hits<=60:
                            raise ValueError("Invalid integer top-five hit count")
                        if not close(v["recall_at5"],hits/60,1e-7):
                            raise ValueError("Incorrect recall in raw run")
                        if v["recall_at5"]+1e-7<prev:
                            raise ValueError("Increasing M lost correct neighbors")
                        prev=v["recall_at5"]
                        if v.get("query_p50_ms",0)<=0 or v.get("query_p95_ms",0)<=0:
                            raise ValueError("Invalid per-run timing")
                sample.append(r)
            base=statistics.median(r["float32_exact_p50_ms"]for r in sample)
            expected=doc["summary"][str(n)][mode]
            if expected["independent_seed_cases"]!=len(SEEDS) or not close(
                expected["exact_float32_median_p50_ms"],base,1e-5):
                raise ValueError("Baseline summary inconsistent")
            summaries[str(n)][mode]={}
            recalls={}
            for name in SCHEMES:
                data=[next(s for s in r["schemes"]if s["name"]==name)for r in sample]
                got=expected["quantization_schemes"][name]
                if not close(got["median_precompute_ms"],statistics.median(
                    s["quantize_precompute_ms"]for s in data)):
                    raise ValueError("Precompute median not reproduced")
                if got["bytes_per_vector_excluding_original_float32"] != n*768+n*4:
                    raise ValueError("Storage summary mismatch")
                results={}
                for index,m in enumerate(CANDIDATES):
                    total=sum(int(s["topk_results"][index]["hits"])for s in data)
                    p50=statistics.median(s["topk_results"][index]["query_p50_ms"]for s in data)
                    p95=statistics.median(s["topk_results"][index]["query_p95_ms"]for s in data)
                    recorded=got["topk"][str(m)]
                    if (recorded["hits"],recorded["top5_opportunities"])!=(total,600):
                        raise ValueError("Hit count not reproducible")
                    if not close(recorded["micro_recall_at5"],total/600) or not close(
                        recorded["median_direct_query_p50_ms"],p50) or not close(
                        recorded["median_p95_query_ms"],p95):
                        raise ValueError("Latency or recall summary mismatch")
                    if not close(recorded["median_speedup_vs_exact"],base/p50,1e-4):
                        raise ValueError("Speedup ratio mismatch")
                    results[str(m)]={"recall_at5":round(total/600,6),"median_p50_ms":round(p50,6)}
                recalls[name]=results
            diff=100*(recalls["per_vector_absmax"]["20"]["recall_at5"]-
                      recalls["fixed127"]["20"]["recall_at5"])
            if not close(diff,expected["M20_recall_improvement_pp"],.00011):
                raise ValueError("M20 improvement delta incorrect")
            summaries[str(n)][mode]={"M20_recall_fixed127":recalls["fixed127"]["20"]["recall_at5"],
                                      "M20_recall_per_vector_absmax":recalls["per_vector_absmax"]["20"]["recall_at5"],
                                      "M20_recall_improvement_pp":round(diff,4),
                                      "M20_p50_fixed127_ms":recalls["fixed127"]["20"]["median_p50_ms"],
                                      "M20_p50_per_vector_absmax_ms":recalls["per_vector_absmax"]["20"]["median_p50_ms"]}
    return {"status":"PASS","independent_seed_datasets":len(runs),
            "precision_methods":SCHEMES,"per_method_top5_opportunities_per_group":600,
            "verified_performance_summary":summaries,
            "limitations":"Synthetic CPU only; no real embeddings, GPU, network or SensorGraft integration"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path,nargs="?",
        default=Path(__file__).parent/"results"/"2026-10-29-quant-scales-60case-holdout.json")
    a=p.parse_args()
    print(json.dumps(validate(json.loads(a.path.read_text())),indent=2))
