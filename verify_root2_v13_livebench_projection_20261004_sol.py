from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root2_v13_livebench_projection_20261004_sol"
EXPECTED={
 "V13.json":"bb631b80eea5a183728fb27e2aff99bbe63f1757",
 "V12.json":"75ca9127a73ca2dd52a49f2f09e2e0ccc384129a",
 "ACTIVATION.json":"04505bc3fca23c448b35cd5ad546bac770f5cb34",
 "CARRIER_VERIFICATION.json":"7657feb404312794db54bf7e53359bbcf475f628",
}
def blob(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,s in EXPECTED.items(): assert blob(SUB/n)==s,(n,blob(SUB/n),s)
v13=json.loads((SUB/"V13.json").read_text())
v12=json.loads((SUB/"V12.json").read_text())
act=json.loads((SUB/"ACTIVATION.json").read_text())
car=json.loads((SUB/"CARRIER_VERIFICATION.json").read_text())

assert v13["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V13"
assert v13["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V12.json"
assert v13["exact_state"]==v12["exact_state"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "root1_positive_gap_count":0,"root2_only_count":16,"root3_only_count":7,
 "root2_and_root3_count":3,"root2_touching_predicates":19
}
# Every pre-existing source binding is byte-for-byte semantically preserved.
for k,val in v12["source_bindings"].items():
 assert v13["source_bindings"][k]==val,k
new=v13["source_bindings"]["livebench_if_thin_adapter_completion"]
assert new["activation_git_blob_sha"]==EXPECTED["ACTIVATION.json"]
assert new["verification_git_blob_sha"]==EXPECTED["CARRIER_VERIFICATION.json"]
assert act["effect"]["thin_adapter_gate_complete"] is True
assert act["effect"]["thin_adapter_fields_proved"]==8
assert car["verified"]["livebench_thin_adapter_after_binding"]=="8_OF_8_PASS"
assert car["verified"]["resource_fit_proved"] is False
assert car["verified"]["fresh_reality_authority"] is False

assert v13["projection_deltas"][:-1]==v12["projection_deltas"]
d=v13["projection_deltas"][-1]
assert d["target"]=="LIVEBENCH_IF_GE_65_7"
assert "THIN_ADAPTER_8_OF_8_COMPLETE" in d["to"]
assert "ZERO_INCREMENTAL_SPEND_OR_ENTITLEMENT" in d["deletion"]
assert v13["waiting_external_facts"]==v12["waiting_external_facts"]
assert v13["exhausted_or_deleted"]==v12["exhausted_or_deleted"]
assert v13["fresh_reality_preserved_not_authorized"]==v12["fresh_reality_preserved_not_authorized"]
assert v13["accounting"]==v12["accounting"] and all(x==0 for x in v13["accounting"].values())
assert v13["execution_authority"] is False
assert v13["promotion_authority"] is False
assert v13["fresh_reality_authority"] is False

old=set(v12["runnable_zero_reality"]); newset=set(v13["runnable_zero_reality"])
assert old <= newset
extra=newset-old
assert extra=={"LIVEBENCH_IF_EXACT_PRECOMMIT_ISOLATION_INSTANTIATION_AND_RESOURCE_FIT_PREFLIGHT__THIN_ADAPTER_8_OF_8_COMPLETE__NO_CASE_EXPOSURE"}
route=v13["livebench_if_isolation_route"]
assert route["thin_adapter_state"]=="8_OF_8_COMPLETE__INDEPENDENT_PUBLIC_RUNNER_PASS"
assert route["zero_incremental_spend_or_entitlement_verified"] is True
assert len(route["remaining_zero_reality"])==3
assert route["separate_authority_gate"]=="EXPLICIT_FRESH_REALITY_AUTHORITY"
assert route["fresh_reality_authority"] is False
assert route["acceptance_credit_delta"]==0

print(json.dumps({
 "status":"PASS","exact_blobs":EXPECTED,
 "v12_semantics_preserved":True,
 "new_livebench_projection_count":1,
 "thin_adapter":"8_OF_8_COMPLETE",
 "acceptance_state":"5_OF_19__12_OF_38__26_UNRESOLVED",
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
