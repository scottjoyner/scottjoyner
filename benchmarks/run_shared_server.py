#!/usr/bin/env python3
"""Bounded, synchronized Unix-socket shared-index CPU benchmark.

One C server holds exactly one read-only synthetic 768D index. Concurrent
Python clients issue small query-ID requests and measure end-to-end latency,
while server responses expose admission queue time and compute time.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import socket
import statistics
import struct
import subprocess
import tempfile
import threading
import time

SOURCE_SHA = "6fc33c4fb5061d02bae11d9daac5fe4dce3b835905f2ddb601b6bae3a093f694"
MODES=["ram","rank","coalesced"]
DISTS=["temporal","clustered"]
THREADS=[1,4]
CLIENTS=[1,4,8]
SEEDS=[20261170,20261171]
N,D,NQ,M=32768,768,12,160
QUERIES_PER_CLIENT=16
QUEUE_LIMIT=8
TIMEOUT_SECONDS=20

def percentile(values, q):
    data=sorted(values)
    return data[int(q*(len(data)-1))]

def recv_all(sock, count):
    data=b""
    while len(data)<count:
        chunk=sock.recv(count-len(data))
        if not chunk:
            raise RuntimeError("Premature socket close")
        data+=chunk
    return data

def available_ram_kib():
    with open("/proc/meminfo",encoding="utf-8") as f:
        for line in f:
            if line.startswith("MemAvailable:"):return int(line.split()[1])
    raise ValueError("Missing MemAvailable")

def run_group(binary, mode, dist, threads, clients, seed, queries=QUERIES_PER_CLIENT, queue=QUEUE_LIMIT):
    with tempfile.TemporaryDirectory(prefix="sg-uds-bench-") as td:
        sockpath=str(Path(td)/"service.sock")
        command=["nice","-n","15",str(binary),sockpath,
                 str(N),str(D),str(NQ),str(seed),dist,mode,str(threads),str(queue)]
        server=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                text=True)
        try:
            ready=server.stdout.readline().strip()
            if not ready.startswith("READY "):
                raise RuntimeError(f"Server failed to initialize: {ready}, {server.poll()}")
            ready_data=dict(item.split("=",1) for item in ready.split()[1:])
            assert int(ready_data["n"])==N and int(ready_data["threads"])==threads
            barrier=threading.Barrier(clients+1,timeout=TIMEOUT_SECONDS)
            def client(index):
                output=[]
                barrier.wait()
                for j in range(queries):
                    qid=(index*3+j)%NQ
                    begin=time.perf_counter_ns()
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
                        conn.settimeout(TIMEOUT_SECONDS)
                        conn.connect(sockpath)
                        conn.sendall(struct.pack("<I",qid))
                        response=recv_all(conn,24)
                    elapsed=time.perf_counter_ns()-begin
                    status,hits,queue_ns,compute_ns=struct.unpack("<IIQQ",response)
                    if status not in (0,1):raise ValueError(f"Worker failed: status {status}")
                    if status==0 and not 0<=hits<=5:raise ValueError("Impossible accuracy")
                    output.append({"status":status,"hits":hits,"qid":qid,
                                   "end_to_end_ms":round(elapsed/1e6,6),
                                   "queued_ms":round(queue_ns/1e6,6),
                                   "compute_ms":round(compute_ns/1e6,6)})
                return output
            with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as ex:
                futures=[ex.submit(client,i) for i in range(clients)]
                barrier.wait()
                began=time.perf_counter_ns()
                trials=[x for future in futures for x in future.result(timeout=TIMEOUT_SECONDS)]
                wall_ms=(time.perf_counter_ns()-began)/1e6
            accepted=[x for x in trials if x["status"]==0]
            rejected=[x for x in trials if x["status"]==1]
            if len(accepted)+len(rejected)!=clients*queries or not accepted:
                raise ValueError("Incomplete request observations")
            if len(accepted)<clients*queries and queue==QUEUE_LIMIT:
                raise ValueError("Unexpected overload in bounded baseline test")
            if not all(x["hits"]==5 for x in accepted):
                raise ValueError("Exact top-five parity failure")
            latencies=[x["end_to_end_ms"] for x in accepted]
            queues=[x["queued_ms"] for x in accepted]
            computes=[x["compute_ms"] for x in accepted]
            record={
                "mode":mode,"distribution":dist,"server_workers":threads,
                "clients":clients,"seed":seed,"queue_limit":queue,
                "queries_per_client":queries,"requests":len(trials),
                "accepted":len(accepted),"rejected":len(rejected),
                "hits":sum(x["hits"] for x in accepted),
                "top5_opportunities":len(accepted)*5,
                "recall_at5":sum(x["hits"] for x in accepted)/(len(accepted)*5),
                "client_wall_ms":round(wall_ms,6),
                "completed_qps":round(len(accepted)*1000/wall_ms,6),
                "client_p50_ms":round(percentile(latencies,.5),6),
                "client_p95_ms":round(percentile(latencies,.95),6),
                "queue_p50_ms":round(percentile(queues,.5),6),
                "queue_p95_ms":round(percentile(queues,.95),6),
                "compute_p50_ms":round(percentile(computes,.5),6),
                "compute_p95_ms":round(percentile(computes,.95),6),
                "server_ready_rss_kib":int(ready_data["rss_kib"]),
                "responses":trials,
            }
            return record
        finally:
            if server.poll() is None:
                server.terminate()
                try:server.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=3)
            if server.stdout:server.stdout.close()
            if server.stderr:server.stderr.close()

def summary(trials):
    result={}
    for dist in DISTS:
        result[dist]={}
        for mode in MODES:
            result[dist][mode]={}
            for threads in THREADS:
                result[dist][mode][str(threads)]={}
                for clients in CLIENTS:
                    group=[x for x in trials if
                           (x["distribution"],x["mode"],x["server_workers"],x["clients"] )==
                           (dist,mode,threads,clients)]
                    if sorted(x["seed"] for x in group)!=SEEDS:
                        raise ValueError("Unreproduced test group")
                    result[dist][mode][str(threads)][str(clients)]={
                        "replicates":len(group),
                        "median_qps":round(statistics.median(x["completed_qps"] for x in group),6),
                        "median_client_p95_ms":round(statistics.median(x["client_p95_ms"] for x in group),6),
                        "median_queue_p95_ms":round(statistics.median(x["queue_p95_ms"] for x in group),6),
                        "median_compute_p95_ms":round(statistics.median(x["compute_p95_ms"] for x in group),6),
                        "median_server_ready_rss_kib":round(statistics.median(x["server_ready_rss_kib"] for x in group),6),
                        "accepted":sum(x["accepted"] for x in group),
                        "rejected":sum(x["rejected"] for x in group),
                    }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--binary",type=Path,required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    if hashlib.sha256(args.source.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError("Benchmark source changed; frozen hash mismatch")
    groups=[(m,d,t,c,s) for d in DISTS for m in MODES
            for t in THREADS for c in CLIENTS for s in SEEDS]
    random.Random(20261170).shuffle(groups)
    records=[]
    for index,(mode,dist,threads,clients,seed) in enumerate(groups,1):
        if available_ram_kib()<8*1024*1024 or shutil.disk_usage("/tmp").free<8*1024**3:
            raise RuntimeError("Controller below preflight minimum RAM or disk")
        rec=run_group(args.binary,mode,dist,threads,clients,seed)
        records.append(rec)
        print(f"PASS {index}/{len(groups)} dist={dist} mode={mode} "
              f"workers={threads} clients={clients} seed={seed} "
              f"qps={rec['completed_qps']:.1f} p95={rec['client_p95_ms']:.2f}ms "
              f"queue_p95={rec['queue_p95_ms']:.2f}ms "
              f"rss={rec['server_ready_rss_kib']}KiB",flush=True)
    doc={
        "schema_version":1,"kind":"synthetic_shared_uds_index_bounded_queue_cpu",
        "date":"2026-10-29",
        "source_sha256":SOURCE_SHA,
        "source_commit":"b121ad090df96d3ecc4e9ee4c16ee7aecefdb8c2",
        "design":{"vectors":N,"dimensions":D,"queries_in_index":NQ,
                  "shortlist":M,"queries_per_client":QUERIES_PER_CLIENT,
                  "queue_limit":QUEUE_LIMIT,"server_workers":THREADS,
                  "clients":CLIENTS,"distributions":DISTS,
                  "modes":MODES,"seeds":SEEDS},
        "trials":records,"summary":summary(records),
        "limitations":[
            "One shared read-only synthetic index within a Unix-domain-socket C server per group; server torn down between trials",
            "Client query identifiers reference server-side synthetic queries; full embedding transport and model encoding not tested",
            "Thread pool workers 1 or 4; queue limit 8; only client counts 1/4/8 (no intentional queue overflow)",
            "Server admission time includes accepting and queue delay, excludes synthetic index initialization",
            "Client wall throughput includes Python socket connection and serialization overhead",
            "Warm file pages may reside in Linux page cache; process VmRSS is not full-node memory or cgroup peak",
            "Two seeds per config with uncontrolled background load: descriptive, not statistically stable",
            "No real SensorGraft/Neo4j production data, media, GPU, ROCm or network",
            "Single-machine loopback UDS; no cross-host network latency",
        ]
    }
    args.output.write_text(json.dumps(doc,separators=(",",":"))+"\n")
    print("COMPLETE",len(records),"groups",sum(x["accepted"] for x in records),"queries",flush=True)
    for dist,modes in doc["summary"].items():
        for mode,workers in modes.items():
            print("SUMMARY",dist,mode,
                  {w:{c:(x["median_qps"],x["median_client_p95_ms"],x["median_queue_p95_ms"],x["median_server_ready_rss_kib"]) for c,x in v.items()} for w,v in workers.items()},
                  flush=True)

if __name__=="__main__":
    main()
