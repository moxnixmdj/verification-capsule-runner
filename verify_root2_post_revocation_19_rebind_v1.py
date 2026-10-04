#!/usr/bin/env python3
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject/root2_post_revocation_19_rebind_v1"

def load(name):
    return json.loads((SUB / name).read_text(encoding="utf-8"))

def blob_sha(name):
    b=(SUB/name).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

cand=load("ROOT2_POST_REVOCATION_19_PREDICATE_REBIND_V1.json")
root=load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
frontier=load("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V18.json")
fver=load("ROOT2_FRONTIER_V18_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
rev=load("LIVEBENCH_FORCED_FAIL_ROOT1_REVOCATION_20261004_V1.json")

expected={
 "terminal_root_state":"e8371418ed39b83b14df874c8eb5e0bdb6a2e603",
 "livebench_forced_fail_revocation":"bbbe29ec26b1f96ba5538ca159f899e316b167e7",
 "frontier_v18":"57d5ee650d4ee250db455d5818899f32aa304918",
 "frontier_v18_independent_verification":"411089263339c4506b641cf08ba9ac13a50ee4c9",
}
files={
 "terminal_root_state":"TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "livebench_forced_fail_revocation":"LIVEBENCH_FORCED_FAIL_ROOT1_REVOCATION_20261004_V1.json",
 "frontier_v18":"ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V18.json",
 "frontier_v18_independent_verification":"ROOT2_FRONTIER_V18_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}
for key, exp in expected.items():
    got=blob_sha(files[key])
    assert got==exp,(key,got,exp)
    assert cand["source_bindings"][key]["git_blob_sha"]==exp

part=root["current_residual_root_partition"]
assert part["unresolved_total"]==26
assert part["root1_positive_gap_count"]==0
assert part["root2_only_count"]==16
assert part["root3_only_count"]==7
assert part["root2_and_root3_count"]==3
assert part["root1_only_count"]==0
assert "LIVEBENCH_IF_GE_65_7" in part["root2_only"]
assert "LIVEBENCH_IF_GE_65_7" not in part.get("root1_only",[])
assert len(part["root2_only"])+len(part["root2_and_root3"])==19

bp=cand["bound_partition"]
assert bp["accepted_families"]==5
assert bp["open_families"]==14
assert bp["proved_atomic"]==12
assert bp["unresolved_atomic"]==26
assert bp["root1_positive_gap_count"]==0
assert bp["root2_only_count"]==16
assert bp["root3_only_count"]==7
assert bp["root2_and_root3_count"]==3
assert bp["root2_touching_predicates"]==19

fs=frontier["exact_state"]
for key in ("accepted_families","open_families","proved_atomic","unresolved_atomic","root1_positive_gap_count","root2_only_count","root3_only_count","root2_and_root3_count"):
    assert fs[key]==bp[key],(key,fs[key],bp[key])
assert fs["root2_touching_predicates"]==19

assert fver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert fver["subject"]["frontier_git_blob_sha"]==expected["frontier_v18"]
assert fver["independent_runner"]["conclusion"]=="success"
assert fver["verified"]["root1_positive_gap_count"]==0
assert fver["verified"]["unresolved_atomic"]==26
assert rev["corrected_current_projection"]["root1_positive_gap_count"]==0
assert rev["corrected_current_projection"]["root2_only"]==16
assert rev["corrected_current_projection"]["root3_only"]==7
assert rev["corrected_current_projection"]["root2_and_root3"]==3

auth=cand["authority"]
assert auth["scheduling_candidate"] is True
for key in ("execution","promotion","fresh_reality","acceptance_credit"):
    assert auth[key] is False
acct=cand["accounting"]
for key in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert acct[key]==0

print(json.dumps({
 "status":"PASS__EXACT_19_PREDICATE_ROOT2_POST_REVOCATION_REBIND",
 "candidate_git_blob_sha":blob_sha("ROOT2_POST_REVOCATION_19_PREDICATE_REBIND_V1.json"),
 "root2_touching_predicates":19,
 "root1_positive_gap_count":0,
 "livebench_class":"ROOT2_ONLY",
 "frontier_v18_git_blob_sha":expected["frontier_v18"],
 "execution_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
