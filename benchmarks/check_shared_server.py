#!/usr/bin/env python3
"""Verify synthetic single-server UDS concurrent retrieval receipts.

Recomputes client-visible p50/p95, queue and compute latency, completed-query
rate, exact top-five parity and source/config provenance from request receipts.
"""
import argparse
import json
import statistics
from pathlib import Path

SHA="6fc33c4fb5061d02bae11d9daac5fe4dce3b835905f2ddb601b6bae3a093f694"
MODES=["ram","rank","coalesced"]
DISTS=["temporal","clustered"]
WORKERS=[1,4]
CLIENTS=[1,4,8]
SEEDS=[20261170,20261171]
PER_CLIENT=16

def close(a,b, tol=.000025):return abs(a-b)<=tol

def pct(values,p):
    x=sorted(values);return x[int(p*(len(x)-1))]

def validate(doc):
    if doc.get("schema_version")!=1 or doc.get("kind")!="synthetic_shared_uds_index_bounded_queue_cpu" or doc.get("source_sha256")!=SHA:
        raise ValueError("Study kind/source mismatch")
    d=doc.get("design",{})
    if (d.get("vectors"),d.get("dimensions"),d.get("queries_in_index"),d.get("shortlist"),
        d.get("queries_per_client"),d.get("queue_limit"),d.get("server_workers"),
        d.get("clients"),d.get("distributions"),d.get("modes"),d.get("seeds")) != (
            32768,768,12,160,PER_CLIENT,8,WORKERS,CLIENTS,DISTS,MODES,SEEDS):
        raise ValueError("Modified benchmark configuration")
    trials=doc.get("trials",[])
    if len(trials)!=72:raise ValueError("Expected 72 groups")
    seen=set();responses=0;all_accepted=0;all_rejected=0
    for row in trials:
        key=(row["distribution"],row["mode"],row["server_workers"],row["clients"],row["seed"])
        if key in seen:raise ValueError("Duplicate result")
        seen.add(key)
        if (key[0] not in DISTS or key[1] not in MODES or key[2] not in WORKERS
                or key[3] not in CLIENTS or key[4] not in SEEDS):
            raise ValueError("Unknown combination")
        if row.get("source_sha256")!=SHA or row.get("queue_limit")!=8:
            raise ValueError("Unknown source/queue")
        raw=row.get("responses",[])
        if len(raw)!=PER_CLIENT*key[3] or row.get("requests")!=len(raw):
            raise ValueError("Lost or duplicated client query")
        busy=sum(r["status"]==1 for r in raw)
        ok=[r for r in raw if r["status"]==0]
        if any(r["status"] not in (0,1) for r in raw):
            raise ValueError("Failed worker/transport request")
        if row["rejected"]!=busy or row["accepted"]!=len(ok):
            raise ValueError("Queue admission accounting mismatch")
        if busy:
            raise ValueError("Unexpected overload in baseline benchmark")
        if any(r["hits"]!=5 or r["compute_ms"]<=0 or r["end_to_end_ms"]<=0 or
               r["queued_ms"]<0 or r["qid"] not in range(12) for r in ok):
            raise ValueError("Invalid exact top-five result or timing")
        if row["top5_opportunities"]!=5*len(ok) or row["hits"]!=5*len(ok) or row["recall_at5"]!=1:
            raise ValueError("Top-five hit aggregation incorrect")
        if row["client_wall_ms"]<=0 or row["server_ready_rss_kib"]<=0:
            raise ValueError("Invalid wall-clock or process memory")
        if not close(row["completed_qps"],len(ok)*1000/row["client_wall_ms"],.0005):
            raise ValueError("Completed query rate mismatch")
        for stat,field,p in [
            ("client_p50_ms","end_to_end_ms",.5),
            ("client_p95_ms","end_to_end_ms",.95),
            ("queue_p50_ms","queued_ms",.5),
            ("queue_p95_ms","queued_ms",.95),
            ("compute_p50_ms","compute_ms",.5),
            ("compute_p95_ms","compute_ms",.95)]:
            if not close(row[stat],pct([r[field]for r in ok],p)):
                raise ValueError("Incorrect latency percentile "+stat)
        responses+=len(raw);all_accepted+=len(ok);all_rejected+=busy
    expected={(d,m,w,c,s)for d in DISTS for m in MODES for w in WORKERS for c in CLIENTS for s in SEEDS}
    if seen!=expected:raise ValueError("Missing expected test group")
    if responses!=4992 or all_accepted!=4992 or all_rejected!=0:
        raise ValueError("Total request count mismatch")
    summary={}
    for dist in DISTS:
        summary[dist]={}
        for mode in MODES:
            summary[dist][mode]={}
            for workers in WORKERS:
                summary[dist][mode][str(workers)]={}
                for clients in CLIENTS:
                    rows=[r for r in trials if
                          (r["distribution"],r["mode"],r["server_workers"],r["clients"])==
                          (dist,mode,workers,clients)]
                    if sorted(r["seed"]for r in rows)!=SEEDS:raise ValueError("Missing repeats")
                    published=doc["summary"][dist][mode][str(workers)][str(clients)]
                    if published["replicates"]!=2 or published["accepted"]!=sum(r["accepted"]for r in rows) or published["rejected"]!=0:
                        raise ValueError("Summary count mismatch")
                    fields={
                        "median_qps":"completed_qps",
                        "median_client_p95_ms":"client_p95_ms",
                        "median_queue_p95_ms":"queue_p95_ms",
                        "median_compute_p95_ms":"compute_p95_ms",
                        "median_server_ready_rss_kib":"server_ready_rss_kib"}
                    for key,raw in fields.items():
                        if not close(published[key],statistics.median(r[raw]for r in rows)):
                            raise ValueError("Wrong summary "+key)
                    summary[dist][mode][str(workers)][str(clients)]={
                        "qps":round(published["median_qps"],2),
                        "end_to_end_p95_ms":round(published["median_client_p95_ms"],3),
                        "queue_p95_ms":round(published["median_queue_p95_ms"],3),
                        "server_rss_kib":published["median_server_ready_rss_kib"]}
    return {"status":"PASS","gated_shared_server_groups":len(trials),
            "accepted_client_requests":all_accepted,"rejected":all_rejected,
            "summary":summary,
            "limitations":"Synthetic UDS server, shared readonly index, 1 or 4 threads, 1/4/8 clients, 2 seeds; not production."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path,nargs="?",
                   default=Path(__file__).parent/"results"/"2026-10-29-shared-server-uds.json")
    args=p.parse_args()
    print(json.dumps(validate(json.loads(args.path.read_text(encoding="utf-8"))),indent=2))
