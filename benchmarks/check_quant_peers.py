#!/usr/bin/env python3
"""Verify CPU quantization peer reproduction on identical synthetic seeds."""
import argparse
import json
from pathlib import Path

SHA = "b95bf19e86cc24f3c360eef782f0e357e6ec63bf61f4cd269070413d5f738e50"
SEEDS = list(range(20261130, 20261135))
HOST_COUNTS = {
    "deathstar-xps-8920": [8192, 32768],
    "scott-lenovo-ideapad-330s-15ikb": [8192, 32768],
    "raspberrypi": [8192],
}
MS=[20,40,80,160]

def verify(doc):
    if doc.get("schema_version")!=1 or doc.get("kind")!="synthetic_quantization_peer_replication":
        raise ValueError("Wrong artifact schema/kind")
    if doc.get("source_sha256")!=SHA or doc.get("seeds")!=SEEDS:
        raise ValueError("Wrong source or seeds")
    hosts=doc.get("hosts",[])
    if len(hosts)!=3 or {h["node"] for h in hosts}!=set(HOST_COUNTS):
        raise ValueError("Wrong host list")
    canonical={}
    total=0
    out={}
    for host in hosts:
        node=host["node"]
        cases=host.get("trials",[])
        sizes=HOST_COUNTS[node]
        if len(cases)!=len(sizes)*len(SEEDS):
            raise ValueError("Missing runs for "+node)
        counts={}
        for n in sizes:
            group=[]
            for seed in SEEDS:
                matching=[r for r in cases if
                          (r.get("vectors"),r.get("seed"),r.get("distribution"))==(n,seed,"clustered")]
                if len(matching)!=1: raise ValueError("Missing or duplicate data")
                r=matching[0]
                if r.get("status")!="PASS" or r.get("sanity_failures")!=0 or (
                    r.get("dimensions"),r.get("queries"),r.get("repeats"))!=(768,12,2):
                    raise ValueError("Invalid run")
                data=[]
                schemes=r.get("schemes",[])
                if [s["name"] for s in schemes]!=["fixed127","per_vector_absmax"]:
                    raise ValueError("Wrong quantization schemes")
                for s in schemes:
                    if [x["candidates"]for x in s["topk_results"]]!=MS:
                        raise ValueError("Wrong candidate sizes")
                    hit_values=[]
                    for x in s["topk_results"]:
                        if x["hits"]!=round(x["hits"]) or not 0<=x["hits"]<=60:
                            raise ValueError("Impossible top5 hit count")
                        if abs(x["recall_at5"]-x["hits"]/60)>1e-7:
                            raise ValueError("Recall inconsistent with raw hits")
                        if x["query_p50_ms"]<=0:raise ValueError("Nonpositive latency")
                        hit_values.append(int(x["hits"]))
                    data.append(hit_values)
                key=(n,seed)
                if key in canonical and canonical[key]!=data:
                    raise ValueError("Same generated data yielded different retrieval hits between hosts")
                canonical[key]=data
                group.append(data)
                total+=1
            fixed=sum(v[0][0]for v in group)
            dynamic=sum(v[1][0]for v in group)
            counts[str(n)]={"fixed127_m20_recall":round(fixed/300,6),
                            "per_vector_m20_recall":round(dynamic/300,6)}
        out[node]=counts
    if total!=25:raise ValueError("Wrong total run count")
    return {"status":"PASS","peer_cpu_runs":total,
            "independent_seed_size_cases":len(canonical),
            "results":out,
            "caveats":"Shared seeds among hosts verify deterministic recall, not independent accuracy"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path,nargs="?",
        default=Path(__file__).parent/"results"/"2026-10-29-quant-scales-peer.json")
    args=p.parse_args()
    print(json.dumps(verify(json.loads(args.path.read_text())),indent=2))
