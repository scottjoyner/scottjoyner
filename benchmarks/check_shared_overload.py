#!/usr/bin/env python3
"""Verify overload of shared read-only UDS retrieval returns explicit BUSY.

All client attempts must have an observed response, and every accepted
request must return an exact top-five synthetic retrieval hit set.
"""
import argparse
import json
from pathlib import Path

SOURCE="6fc33c4fb5061d02bae11d9daac5fe4dce3b835905f2ddb601b6bae3a093f694"
MODES=["ram","rank","coalesced"]
DISTS=["temporal","clustered"]
SEEDS=[20261172,20261173,20261174]
def verify(doc):
    if doc.get("schema_version")!=1 or doc.get("kind")!="synthetic_shared_uds_overload_admission" or doc.get("source_sha256")!=SOURCE:
        raise ValueError("Unknown artifact")
    d=doc.get("design",{})
    if (d.get("distributions"),d.get("modes"),d.get("seeds"),
        d.get("workers"),d.get("queue_limit"),d.get("clients"),d.get("queries_per_client"),
        d.get("vectors"),d.get("dimensions"),d.get("shortlist_m")) != (
        DISTS,MODES,SEEDS,1,2,24,1,32768,768,160):
        raise ValueError("Overload design modified")
    rows=doc.get("results",[])
    if len(rows)!=18:raise ValueError("Wrong number of overload experiments")
    seen=set();accepted=0;busy=0
    per_mode={}
    for x in rows:
        key=(x["distribution"],x["mode"],x["seed"])
        if key in seen:raise ValueError("Duplicate test group")
        seen.add(key)
        if key[0] not in DISTS or key[1] not in MODES or key[2] not in SEEDS:
            raise ValueError("Unrecognized test")
        if (x["server_workers"],x["clients"],x["queue_limit"],x["queries_per_client"],
            x["requests"]) != (1,24,2,1,24):
            raise ValueError("Unexpected workload")
        raw=x.get("responses",[])
        if len(raw)!=24 or any(r.get("status") not in (0,1) for r in raw):
            raise ValueError("Missing or invalid response")
        successes=[r for r in raw if r["status"]==0]
        rejections=[r for r in raw if r["status"]==1]
        if len(successes)!=x["accepted"] or len(rejections)!=x["rejected"]:
            raise ValueError("Summary status mismatch")
        if not successes or not rejections:
            raise ValueError("Did not exercise acceptance AND bounded rejection")
        if any(r["hits"]!=5 for r in successes):
            raise ValueError("Incorrect accepted retrieval")
        if x["hits"]!=5*len(successes) or x["top5_opportunities"]!=5*len(successes) or x["recall_at5"]!=1:
            raise ValueError("Incorrect accuracy aggregation")
        if x["client_wall_ms"]<=0 or x["server_ready_rss_kib"]<=0:
            raise ValueError("Missing performance evidence")
        accepted+=len(successes);busy+=len(rejections)
        per_mode.setdefault(key[1],{"accepted":0,"busy":0})
        per_mode[key[1]]["accepted"]+=len(successes)
        per_mode[key[1]]["busy"]+=len(rejections)
    expected={(d,m,s)for d in DISTS for m in MODES for s in SEEDS}
    if seen!=expected or accepted+busy!=432:
        raise ValueError("Incomplete matrix or unaccounted requests")
    if doc.get("summary") != {
        "groups":18,"requests":432,"accepted":accepted,"explicit_busy":busy,
        "all_successful_retrievals_exact_top5":True
    }:
        raise ValueError("Publication summary incorrect")
    return {"status":"PASS","overload_groups":18,"total_requests":432,
            "accepted":accepted,"explicit_busy":busy,
            "modes":per_mode,
            "caveat":"Synthetic overload rejection, not an implementation of retry or persistence"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path,nargs="?",
                   default=Path(__file__).parent/"results"/"2026-10-29-shared-server-overload.json")
    args=p.parse_args()
    print(json.dumps(verify(json.loads(args.path.read_text(encoding="utf-8"))),indent=2))
