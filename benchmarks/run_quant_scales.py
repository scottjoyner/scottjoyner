#!/usr/bin/env python3
"""Frozen design: compare fixed127 versus per-vector absmax int8 on held-out seeds.

This is a synthetic CPU-only retrieval experiment, not GPU/model fine-tuning.
The candidate sizes 20,40,80,160 and seed range are fixed in this script.
"""
import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path

C_SOURCE_SHA="b95bf19e86cc24f3c360eef782f0e357e6ec63bf61f4cd269070413d5f738e50"
SEEDS=list(range(20261120,20261130))
SIZES=[8192,32768]
MODES=["independent","temporal","clustered"]
MS=[20,40,80,160]
QUERIES=12
REPEATS=2

def summarize(rows):
    output={}
    for n in SIZES:
        output[str(n)]={}
        for mode in MODES:
            cases=[x for x in rows if x["vectors"]==n and x["distribution"]==mode]
            if [x["seed"] for x in cases]!=SEEDS:
                raise ValueError("Missing expected seed in group")
            baseline=statistics.median(x["float32_exact_p50_ms"] for x in cases)
            schemes={}
            for name in ["fixed127","per_vector_absmax"]:
                data=[next(z for z in row["schemes"] if z["name"]==name) for row in cases]
                opts={}
                total=QUERIES*5*len(data)
                for idx,m in enumerate(MS):
                    hits=sum(round(x["topk_results"][idx]["recall_at5"]*(QUERIES*5))for x in data)
                    median=statistics.median(x["topk_results"][idx]["query_p50_ms"]for x in data)
                    opts[str(m)]={"hits":hits,"top5_opportunities":total,
                                  "micro_recall_at5":round(hits/total,6),
                                  "median_direct_query_p50_ms":round(median,6),
                                  "median_p95_query_ms":round(statistics.median(
                                    x["topk_results"][idx]["query_p95_ms"]for x in data),6),
                                  "median_speedup_vs_exact":round(baseline/median,4)}
                schemes[name]={
                    "median_precompute_ms":round(statistics.median(x["quantize_precompute_ms"] for x in data),6),
                    "bytes_per_vector_excluding_original_float32": n*768+n*4,
                    "topk":opts,
                }
            output[str(n)][mode]={
                "independent_seed_cases":len(cases),
                "exact_float32_median_p50_ms":round(baseline,6),
                "quantization_schemes":schemes,
                "M20_recall_improvement_pp":round(100*(schemes["per_vector_absmax"]["topk"]["20"]["micro_recall_at5"]-
                                                          schemes["fixed127"]["topk"]["20"]["micro_recall_at5"]),4),
            }
    return output

def run(args):
    if hashlib.sha256(args.source.read_bytes()).hexdigest()!=C_SOURCE_SHA:
        raise ValueError("Source SHA-256 differs from frozen program")
    observations=[]
    for n in SIZES:
        for mode in MODES:
            for seed in SEEDS:
                command=[str(args.binary),str(n),"768",str(QUERIES),str(REPEATS),str(seed),mode]
                p=subprocess.run(command,check=True,capture_output=True,text=True,timeout=75)
                x=json.loads(p.stdout)
                if (x.get("status")!="PASS" or x.get("sanity_failures")!=0 or
                    (x["vectors"],x["dimensions"],x["seed"],x["distribution"],x["queries"],x["repeats"])
                       != (n,768,seed,mode,QUERIES,REPEATS) or
                    [s["name"] for s in x["schemes"]] != ["fixed127","per_vector_absmax"]):
                    raise ValueError(f"Failed correctness validation n={n},mode={mode},seed={seed}")
                for s in x["schemes"]:
                    if [v["candidates"] for v in s["topk_results"]]!=MS:
                        raise ValueError("Unexpected candidate sizes")
                    if any(v["query_p50_ms"]<=0 or v["recall_at5"]<0 or v["recall_at5"]>1
                           for v in s["topk_results"]):
                        raise ValueError("Invalid measurement")
                    if any(s["topk_results"][j]["recall_at5"]+1e-7 < s["topk_results"][j-1]["recall_at5"]
                           for j in range(1,len(MS))):
                        raise ValueError("Recall decreased as candidates increased")
                observations.append(x)
                values={s["name"]:s["topk_results"][0]["recall_at5"] for s in x["schemes"]}
                print(f"PASS n={n} mode={mode} seed={seed} M20={values}",flush=True)
    summary=summarize(observations)
    doc={
        "schema_version":1,"kind":"synthetic_cpu_quant_fixed127_vs_per_vector_absmax_holdout",
        "date":"2026-10-29","source_sha256":C_SOURCE_SHA,
        "seed_range":SEEDS,"dimensions":768,"queries":QUERIES,"repeats":REPEATS,
        "vector_counts":SIZES,"distribution_types":MODES,"candidate_sizes":MS,
        "experiment_design":"Fixed in code before evaluation; synthetic CPU 8-bit fixed scale vs absmax per-vector with exact float32 rerank",
        "runs":observations,"summary":summary,
        "limitations":[
            "Synthetic normalized vectors and generated queries, not real dashcam or neural embeddings",
            "Only one Linux host, no controlled CPU frequency/thermal or external load",
            "All variants use exact float32 top-five reference and an int8 brute-force top-M candidate scan",
            "Each direct query timer includes its own int8 scan and float32 rerank; one-time vector quantization/preparation measured separately",
            "Per-vector absmax stores an additional 4-byte scale per vector; float32 source vectors retained for reranking",
            "No production SensorGraft DB indexing, ANN, ROCm, concurrency, bandwidth, or network endpoints",
            "Averaged top-five hits are not independent real-world relevance labels",
            "This study is not a probabilistic recall guarantee"
        ]}
    args.out.write_text(json.dumps(doc,separators=(",",":"))+"\n",encoding="utf-8")
    print("SUMMARY",json.dumps(summary,separators=(",",":")),flush=True)
    print("EVIDENCE",args.out,"CASES",len(observations),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    run(p.parse_args())
