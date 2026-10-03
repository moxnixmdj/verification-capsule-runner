#!/usr/bin/env python3
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime import root2_proof_hypergraph_v1 as opt

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    assert blob(ROOT/rel)==expected,(rel,blob(ROOT/rel),expected)

v=json.loads((ROOT/"canonical/governance/ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json").read_text())
assert v["authority"]["route_inventory_git_blob_sha"]==m["brain_route_inventory_blob_sha"]
assert len(v["surfaces"])==14
preds=[p for s in v["surfaces"] for p in s["predicates"]]
assert len(preds)==15 and len(set(preds))==15
shared=[s for s in v["surfaces"] if len(s["predicates"])>1]
assert len(shared)==1 and shared[0]["surface"]=="AA-Briefcase v1.1"
assert v["incremental_spend_usd"]==0 and v["fresh_reality_authority"] is False

g=json.loads((ROOT/"canonical/governance/ROOT2_PROOF_HYPERGRAPH_V1.json").read_text())
assert g["acceptance_credit_delta"]==0 and g["promotion_authority"] is False

assert opt.binary_prefix_decision(successes=7,observed=7,total=10,threshold="0.7")["status"]=="GUARANTEED_PASS"
assert opt.binary_prefix_decision(successes=0,observed=4,total=10,threshold="0.7")["status"]=="GUARANTEED_FAIL"
assert opt.bounded_metric_decision(lower="65.7",upper="70",target="65.7")["status"]=="GUARANTEED_PASS"

rows=opt.rank_actions([
 {"id":"paid","safe":True,"incremental_spend_usd":1,"closes":["p"],"p_close_low":1,"time_high":1},
 {"id":"free","safe":True,"incremental_spend_usd":0,"closes":["p"],"p_close_low":"1/2","information_gain_low":1,"time_high":1}
],open_predicates=["p"])
assert [x["id"] for x in rows]==["free"]

cover=opt.minimum_guaranteed_cover([
 {"id":"ab","safe":True,"guaranteed":True,"closes":["a","b"],"p_close_low":1,"p_close_high":1,"time_high":1},
 {"id":"c","safe":True,"guaranteed":True,"closes":["c"],"p_close_low":1,"p_close_high":1,"time_high":1}
],open_predicates=["a","b","c"])
assert cover["status"]=="GUARANTEED_FULL_COVER" and cover["action_count"]==2

print(json.dumps({"pass":True,"schema":"PROJECT_BRAIN_ROOT2_PROOF_HYPERGRAPH_PUBLIC_RUNNER_RESULT_V1","status":"PASS__EXACT_BLOBS__14_SURFACES_15_PREDICATES__ROBUST_OPTIMIZER__EARLY_STOPPING__ZERO_CREDIT"},sort_keys=True))
