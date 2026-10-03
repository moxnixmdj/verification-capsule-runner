#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "pointer":("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V13_CANDIDATE_V1.json","9ae934eb9971d59bf205823317f44e97709fa618"),
 "active":("canonical/governance/TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_V1.json","d6546a99a62c77b79ae0b169e822ca4f636eea72"),
 "receipt":("canonical/verification/TERMINAL_SCHEDULING_V13_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","407313a62efa87c5f0fced98e25732b973b78baf"),
 "candidate":("canonical/governance/TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_CANDIDATE_V1.json","2b597ea1840196623a2d7e31f9c613cd993ec6ba"),
}
def blob(p):
 raw=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]
 assert blob(p)==s,(k,blob(p),s)
 return json.loads((ROOT/p).read_text(encoding="utf-8"))
pointer,active,receipt,candidate=[load(k) for k in ("pointer","active","receipt","candidate")]

def validate(p):
 e=[]
 if p.get("schema")!="PROJECT_BRAIN_TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V13_CANDIDATE_V1": e.append("SCHEMA")
 ca=p.get("current_authority") or {}
 if ca.get("path")!="canonical/governance/TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_V1.json": e.append("ACTIVE_PATH")
 if ca.get("git_blob_sha")!=FILES["active"][1]: e.append("ACTIVE_HASH")
 live=p.get("live_world") or {}
 got=(live.get("registry_predicates"),live.get("proved_predicates"),live.get("unresolved_predicates"),live.get("opus55_acceptance"),live.get("active_zero_reality_requirements"),live.get("active_nondominated_certificates"),live.get("zero_reality_covered_predicates"),live.get("primitive_zero_reality_work_units"),live.get("matched_priority_child_facts"))
 if got!=(38,11,27,"4/19_PASS__15/19_OPEN",17,14,25,31,16): e.append("LIVE_WORLD")
 if live.get("direct_reality_blocked_predicates")!=["FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]: e.append("DIRECT_REALITY")
 r=p.get("mandatory_tool_discovery_retrieval") or {}
 if r.get("authority")!="V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE": e.append("V5_AUTHORITY")
 for k in ("mandatory","strict_success_only_source_cell_consumption_required","transient_failures_retryable_and_unconsumed","all_selected_cells_required_before_epoch_consumption"):
  if r.get(k) is not True: e.append("TRUE:"+k)
 for k in ("partial_batch_epoch_consumption_allowed","off_domain_result_may_satisfy_source_cell","consumed_cell_replay_allowed","empty_or_failed_attempt_proves_nonexistence"):
  if r.get(k) is not False: e.append("FALSE:"+k)
 for k in ("new_reality_units_consumed","incremental_spend_usd","acceptance_credit_delta","capability_credit_delta","family_credit_delta","ownership_credit_delta"):
  if p.get(k)!=0: e.append("NONZERO:"+k)
 for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
  if p.get(k) is not False: e.append("AUTHORITY:"+k)
 return sorted(set(e))

assert not validate(pointer),validate(pointer)
assert active["verified_candidate"]["git_blob_sha"]==FILES["candidate"][1]
assert active["independent_verification"]["git_blob_sha"]==FILES["receipt"][1]
assert active["independent_verification"]["conclusion"]=="success"
assert receipt["independent_runner"]["conclusion"]=="success"
assert receipt["verified"]["active_zero_reality_requirements"]==17
assert receipt["verified"]["primitive_zero_reality_work_units"]==31
assert receipt["verified"]["tool_discovery_retrieval_authority"]=="V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
assert receipt["verified"]["fresh_reality_authority"] is False

m=copy.deepcopy(pointer); m["current_authority"]["git_blob_sha"]="0"*40
assert "ACTIVE_HASH" in validate(m)
m=copy.deepcopy(pointer); m["mandatory_tool_discovery_retrieval"]["authority"]="V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
assert "V5_AUTHORITY" in validate(m)
m=copy.deepcopy(pointer); m["live_world"]["proved_predicates"]=12
assert "LIVE_WORLD" in validate(m)
m=copy.deepcopy(pointer); m["fresh_reality_authority"]=True
assert "AUTHORITY:fresh_reality_authority" in validate(m)
m=copy.deepcopy(pointer); m["acceptance_credit_delta"]=1
assert "NONZERO:acceptance_credit_delta" in validate(m)

print("TERMINAL_SCHEDULING_V13_POINTER_VERIFIED")
print(json.dumps({"pointer_blob":FILES["pointer"][1],"active_blob":FILES["active"][1],"receipt_blob":FILES["receipt"][1],"candidate_blob":FILES["candidate"][1],"live_world":"4_OF_19__11_OF_38__17_REQ__31_UNITS","retrieval":"STRICT_V5","fresh_reality_authority":False},sort_keys=True))
