#!/usr/bin/env python3
"""Exercise BUSY rejection of shared synthetic index with bounded admission.

24 simultaneous clients send one request each against a single worker and
two-slot FIFO. Never drops a request silently: successful retrieval and
explicit BUSY responses must account for all requests.
"""
import argparse
import hashlib
import json
from pathlib import Path
from run_shared_server import run_group, SOURCE_SHA

MODES=["ram","rank","coalesced"]
DISTS=["temporal","clustered"]
SEEDS=[20261172,20261173,20261174]

def execute(args):
    if hashlib.sha256(args.source.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError("Shared synthetic C server source differs")
    results=[]
    for dist in DISTS:
        for mode in MODES:
            for seed in SEEDS:
                record=run_group(args.binary,mode,dist,1,24,seed,queries=1,queue=2)
                if record["accepted"]+record["rejected"]!=24 or record["recall_at5"]!=1:
                    raise ValueError("Silent lost request or incorrect accepted retrieval")
                if record["rejected"]<=0 or record["rejected"]>=24:
                    raise ValueError("Overload test did not exercise explicit rejection and success")
                results.append(record)
                print(f"PASS {dist}/{mode} seed={seed} accepted={record['accepted']} "
                      f"busy={record['rejected']} p95={record['client_p95_ms']:.3f}ms",flush=True)
    doc={
        "schema_version":1,
        "kind":"synthetic_shared_uds_overload_admission",
        "date":"2026-10-29",
        "source_sha256":SOURCE_SHA,
        "design":{"distributions":DISTS,"modes":MODES,"seeds":SEEDS,
                  "workers":1,"queue_limit":2,"clients":24,"queries_per_client":1,
                  "vectors":32768,"dimensions":768,"shortlist_m":160},
        "results":results,
        "summary":{
            "groups":len(results),
            "requests":sum(x["requests"] for x in results),
            "accepted":sum(x["accepted"] for x in results),
            "explicit_busy":sum(x["rejected"] for x in results),
            "all_successful_retrievals_exact_top5":all(x["recall_at5"]==1 for x in results),
        },
        "limitations":[
            "Deliberately overloaded one-worker/two-queue-slot synthetic Unix socket service",
            "Repeated seeds across RAM and file-backed modes; not independent relevance cases",
            "An explicit BUSY status is not a lossless retry mechanism; client retry/backoff not tested",
            "Connection backlog and Python scheduling influence observed number of rejected requests",
            "Only synthetic vectors and read-only index; no real traces, fleet API, ROCm or production data",
        ]
    }
    args.output.write_text(json.dumps(doc,separators=(",",":"))+"\n")
    print("SUMMARY",json.dumps(doc["summary"]),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    execute(p.parse_args())
