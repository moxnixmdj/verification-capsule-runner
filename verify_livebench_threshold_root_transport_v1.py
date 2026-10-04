from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OLD_ROOT=ROOT/"subject/livebench_direct_rebind_v2/root.json"
NEW_ROOT=ROOT/"subject/root2_output_only_threshold_activation_v1_20261004/TERMINAL_ROOT_CAUSE_STATE_V1.json"
OLD_ACT=ROOT/"subject/livebench_direct_authority_activation_v1/activation.json"
V2=ROOT/"subject/livebench_threshold_root_transport_v1/activation_v2.json"
OLD_VERIFY=ROOT/"subject/livebench_threshold_root_transport_v1/prior_activation_verification.json"
THRESH_VERIFY=ROOT/"subject/livebench_threshold_root_transport_v1/threshold_projection_verification.json"

EXPECTED={
 OLD_ROOT:"e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59",
 NEW_ROOT:"601e82d00104b4ed36ee5968ad966a0c02e627c1",
 OLD_ACT:"08929577573866dc2bead65a19a856a6b4e152d2",
 V2:"d410d6952cb34f2fd3fb4dc48bf2a613d11c57d1",
 OLD_VERIFY:"34e65d54026fd246c76e0dc3ded8f9f8a1b2a4d9",
 THRESH_VERIFY:"eef494009e47b758a99ab48649e050c332e4988a",
}
def blob(p):
 data=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for p,s in EXPECTED.items():
 assert blob(p)==s,(p,blob(p),s)

old=json.loads(OLD_ROOT.read_text()); new=json.loads(NEW_ROOT.read_text())
old_act=json.loads(OLD_ACT.read_text()); v2=json.loads(V2.read_text())
old_v=json.loads(OLD_VERIFY.read_text()); th_v=json.loads(THRESH_VERIFY.read_text())

def diff(a,b,path="",out=None):
 if out is None: out=[]
 if a==b:return out
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)):
   diff(a.get(k),b.get(k),f"{path}.{k}" if path else k,out)
 else: out.append(path)
 return out

assert diff(old,new)==["scheduler_policy.root2_output_only_threshold_dag"]
overlay=new["scheduler_policy"]["root2_output_only_threshold_dag"]
assert overlay["execution_authority"] is False
assert overlay["promotion_authority"] is False
assert overlay["fresh_reality_authority"] is False
assert overlay["acceptance_credit_delta"]==0

for r in (old,new):
 part=r["current_residual_root_partition"]
 assert "LIVEBENCH_IF_GE_65_7" in part["root2_only"]
 assert part["root2_only_count"]==16 and part["root3_only_count"]==7 and part["root2_and_root3_count"]==3
 assert r["current_acceptance"]["accepted_families"]==5
 assert r["current_acceptance"]["proved_atomic"]==12
 assert r["current_acceptance"]["unresolved_atomic"]==26

assert old_v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert old_v["verified_activation"]["git_blob_sha"]==EXPECTED[OLD_ACT]
assert th_v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert th_v["subjects"]["root_state_git_blob_sha"]==EXPECTED[NEW_ROOT]
assert th_v["verified"]["fresh_reality_authority"] is False
assert th_v["verified"]["execution_authority"] is False

assert v2["schema"]=="PROJECT_BRAIN_LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V2"
assert v2["authorized_predicates"]==["LIVEBENCH_IF_GE_65_7"]
assert v2["root_state_transport"]["from_git_blob_sha"]==EXPECTED[OLD_ROOT]
assert v2["root_state_transport"]["to_git_blob_sha"]==EXPECTED[NEW_ROOT]
assert v2["root_state_transport"]["independently_observed_exact_delta"]==["scheduler_policy.root2_output_only_threshold_dag"]
assert v2["authority_basis"]["root_state"]["git_blob_sha"]==EXPECTED[NEW_ROOT]
assert v2["exact_execution_binding"]==old_act["exact_execution_binding"]
assert v2["point_of_use_gates_before_any_terminal_case_read"]==old_act["point_of_use_gates_before_any_terminal_case_read"]
assert v2["scope_firewall"]["predicate_local_fresh_reality_authority"] is True
assert v2["scope_firewall"]["global_fresh_reality_authority"] is False
assert v2["scope_firewall"]["all_other_unresolved_predicates_authorized"] is False
assert v2["authority"]=={
 "execution":True,"predicate_local_fresh_reality":True,"global_fresh_reality":False,
 "promotion":False,"acceptance_credit":False
}
assert v2["accounting"]["terminal_cases_consumed"]==0
assert v2["accounting"]["acceptance_credit_delta"]==0
print(json.dumps({
 "schema":"PROJECT_BRAIN_LIVEBENCH_THRESHOLD_ROOT_TRANSPORT_PUBLIC_VERIFIER_V1",
 "pass":True,
 "old_root":EXPECTED[OLD_ROOT],"new_root":EXPECTED[NEW_ROOT],
 "exact_delta":["scheduler_policy.root2_output_only_threshold_dag"],
 "transported_predicate":"LIVEBENCH_IF_GE_65_7",
 "global_fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
