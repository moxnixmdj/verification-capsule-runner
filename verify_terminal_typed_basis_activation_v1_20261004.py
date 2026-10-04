from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_typed_basis_activation_v1_20261004"
VER=SUB/"SUBJECT_VERIFICATION.json"
ACT=SUB/"ACTIVATION_V1.json"

EXPECTED_VER="db20ccb4b3a46622aca640352469f57e0e6d204c"
EXPECTED_ACT="36bb51590145761f2708f882eac343f36ee06038"

def blob(path: Path)->str:
    d=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

assert blob(VER)==EXPECTED_VER
assert blob(ACT)==EXPECTED_ACT

v=json.loads(VER.read_text())
a=json.loads(ACT.read_text())

assert v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert v["independent_runner"]["repository"]=="moxnixmdj/verification-capsule-runner"
assert v["independent_runner"]["pull_request"]==1713
assert v["independent_runner"]["merge_commit"]=="df3ea6e778264a4f576d031edcd890f16e5feb5c"
assert v["independent_runner"]["workflow_run_id"]==37182710243
assert v["independent_runner"]["workflow_job_id"]==111378324110
assert v["independent_runner"]["conclusion"]=="success"
assert v["subjects"]["runtime"]["git_blob_sha"]=="c46dbe13b1ba38fed088272db0d8d89e273efdbd"
assert v["subjects"]["governance"]["git_blob_sha"]=="768115e47787a801b972b475675396032c17eeab"
assert v["subjects"]["arena_correction"]["git_blob_sha"]=="5a2d2b3ac44927bbe7295369b775c46605fe540c"
assert v["execution_authority"] is False
assert v["promotion_authority"] is False
assert v["fresh_reality_authority"] is False
assert v["accounting"]["acceptance_credit_delta"]==0
assert v["accounting"]["family_credit_delta"]==0

assert a["schema"]=="PROJECT_BRAIN_TERMINAL_TYPED_MINIMUM_CERTIFICATE_BASIS_ACTIVATION_V1"
assert a["status"].startswith("CANDIDATE_ACTIVATION")
assert a["subjects"]["planner"]["git_blob_sha"]=="c46dbe13b1ba38fed088272db0d8d89e273efdbd"
assert a["subjects"]["contract"]["git_blob_sha"]=="768115e47787a801b972b475675396032c17eeab"
assert a["relative_elo_rule"]["affected"]==[
 "PROWORK_GDPVAL_GE_1846",
 "PROWORK_AA_BRIEFCASE_GE_1822",
 "ARTIFACT_AA_BRIEFCASE_GE_1822",
]
assert a["isolation_binding"]["generic_runtime"]=="canonical/runtime/generic_precommit_isolation_theorem_v1.py"
assert a["isolation_binding"]["shadow_lease_policy"]=="canonical/governance/SHADOW_REALITY_LEASE_POLICY_V1.json"
assert a["scheduling_authority"] is False
assert a["execution_authority"] is False
assert a["promotion_authority"] is False
assert a["fresh_reality_authority"] is False
assert a["independent_activation_verification_required"] is True
assert a["accounting"]["acceptance_credit_delta"]==0
assert "ROOT2_ROOT3_AND_CURRENT_TERMINAL_COUNTS_REMAIN_UNCHANGED" in a["hard_rules"]

print(json.dumps({
 "status":"PASS",
 "subject_verification_blob":EXPECTED_VER,
 "activation_candidate_blob":EXPECTED_ACT,
 "activation_semantics_consistent":True,
 "relative_elo_guard_bound":True,
 "existing_isolation_reused":True,
 "scheduling_authority_before_final_activation":False,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
