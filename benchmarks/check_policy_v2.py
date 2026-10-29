#!/usr/bin/env python3
"""Independently validate post-hoc V2 shortlist second-holdout evidence.

Policy V2 was selected after a FAILED first holdout and fixed before this
new seed range. This verifier tests raw data and recomputes summary metrics.
"""
import argparse
import json
import statistics
from pathlib import Path

EXPECTED_SOURCE = "6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec"
OLD_POLICY = {"independent": 10, "clustered": 40}
NEW_POLICY = {"independent": 20, "clustered": 80}
CANDIDATES = [5, 10, 20, 40, 80, 160]
START = 20261054


def validate(doc):
    if doc.get("kind") != "synthetic_cpu_second_disjoint_holdout" or doc.get("schema_version") != 1:
        raise ValueError("Wrong study type")
    if doc.get("c_source_sha256") != EXPECTED_SOURCE or doc.get("seed_start") != START:
        raise ValueError("Source/seed provenance mismatch")
    if doc.get("policy_v1_failed_first_holdout") != OLD_POLICY or doc.get(
            "policy_v2_precommitted_to_second_holdout") != NEW_POLICY:
        raise ValueError("Policies differ from precommit")
    if (doc.get("vectors"),doc.get("dimensions"),doc.get("queries"),doc.get("repeats")) != (
            32768,768,12,2):
        raise ValueError("Workload mismatch")
    seeds = doc.get("seed_values", [])
    if not seeds or seeds != list(range(START,START+len(seeds))):
        raise ValueError("Seed range is missing, reordered or overlapping calibration")
    if len(seeds) > 50:
        raise ValueError("Unexpected number of seeds")
    rows = doc.get("records", [])
    if len(rows) != 2*len(seeds):
        raise ValueError("Missing trials")
    summaries = {}
    seen = set()
    for mode, m in NEW_POLICY.items():
        mode_rows = []
        for seed in seeds:
            pair = [r for r in rows if r.get("mode")==mode and r.get("seed")==seed]
            if len(pair)!=1:
                raise ValueError("Missing or duplicate trial")
            r=pair[0]
            seen.add((mode,seed))
            if r.get("exact_float32_p50_ms",0)<=0 or r.get("prequery_quantize_ms",0)<=0:
                raise ValueError("Invalid source measurements")
            opts = r.get("options", [])
            if [v.get("m") for v in opts] != CANDIDATES:
                raise ValueError("Missing shortlist sizes")
            values = [v.get("recall_at_5",-1) for v in opts]
            if any(not 0<=v<=1 for v in values):
                raise ValueError("Recall outside valid range")
            if any(values[i+1] + 1e-6 < values[i] for i in range(5)):
                raise ValueError("Larger shortlist lowered recall")
            if any(v.get("direct_query_p50_ms",0)<=0 for v in opts):
                raise ValueError("Invalid latency")
            mode_rows.append(r)
        num = len(mode_rows)*12*5
        mean = {}
        for i,c in enumerate(CANDIDATES):
            hits = sum(round(r["options"][i]["recall_at_5"]*12*5) for r in mode_rows)
            mean[str(c)] = {
                "recall_at_5": round(hits/num,6),
                "median_query_p50_ms": round(statistics.median(
                    r["options"][i]["direct_query_p50_ms"] for r in mode_rows),6),
                "hits": hits,
            }
        expected = doc["summary"][mode]
        for label, target in [("old",OLD_POLICY[mode]),("new",m)]:
            policy = expected[label+"_policy"]
            if policy["hits"]!=mean[str(target)]["hits"] or policy["top5_opportunities"]!=num:
                raise ValueError("Policy hit count mismatch")
            if abs(policy["recall_at_5"]-mean[str(target)]["recall_at_5"])>0.000001:
                raise ValueError("Policy recall mismatch")
            if abs(policy["median_direct_query_p50_ms"]-mean[str(target)]["median_query_p50_ms"])>0.000001:
                raise ValueError("Policy timing mismatch")
        actual_pass = mean[str(m)]["hits"]/num >= .99
        if expected["new_policy_pass_99pct_recall"]!=actual_pass:
            raise ValueError("Target status mismatch")
        summaries[mode]={"old_policy_m":OLD_POLICY[mode],
                         "old_recall":mean[str(OLD_POLICY[mode])]["recall_at_5"],
                         "new_policy_m":m,
                         "new_recall":mean[str(m)]["recall_at_5"],
                         "new_pass_99":actual_pass,
                         "new_query_p50_ms":mean[str(m)]["median_query_p50_ms"]}
    if len(seen)!=len(rows):
        raise ValueError("Unrecognized trials")
    return {"status":"PASS","validated_runs":len(rows),
            "independent_seed_datasets":len(seeds),"summary":summaries,
            "limits":"Synthetic CPU-only; all distributions use the same generator family"}


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("path",type=Path,nargs="?",
        default=Path(__file__).parent/"results"/"2026-10-29-policy-v2-second-holdout.json")
    args=ap.parse_args()
    print(json.dumps(validate(json.loads(args.path.read_text(encoding="utf-8"))),indent=2))
