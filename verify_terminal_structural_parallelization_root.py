from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_structural_parallelization_root_20261004_sol"
EXPECTED={
 "ROOT.json":"e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59",
 "GENERIC_ACTIVATION.json":"89b3d8cbbc3b9e0822870ee803fb99c37a82d209",
 "GENERIC_VERIFICATION.json":"e9e07a85e7a932ba7ce024c77897ab9016c72ce4",
 "TYPED_VERIFICATION.json":"069ac4d25f82b62e0ae03e7eb9ae30a3c1a96628",
}
def git_blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

root=json.loads((SUB/"ROOT.json").read_text())
ga=json.loads((SUB/"GENERIC_ACTIVATION.json").read_text())
gv=json.loads((SUB/"GENERIC_VERIFICATION.json").read_text())
tv=json.loads((SUB/"TYPED_VERIFICATION.json").read_text())

assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "total_families":19,"total_atomic":38,"terminal":False,
}
part=root["current_residual_root_partition"]
assert (part["root1_positive_gap_count"],part["root2_only_count"],part["root3_only_count"],part["root2_and_root3_count"])==(0,16,7,3)

r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"].endswith("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V12.json")
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False

typed=root["scheduler_policy"]["typed_minimum_certificate_basis"]
assert typed["runtime_git_blob_sha"]=="b42c81e04109e1ff081517672b397390bb3749e0"
assert typed["verification_git_blob_sha"]==EXPECTED["TYPED_VERIFICATION.json"]
assert typed["typed_obligations"]==29
assert typed["comparator_strength_obligations"]==19
assert typed["scope_completeness_obligations"]==10
assert typed["execution_authority"] is False
assert typed["promotion_authority"] is False
assert typed["fresh_reality_authority"] is False
assert typed["acceptance_credit_delta"]==0

generic=root["scheduler_policy"]["generic_precommit_isolation"]
assert generic["activation_git_blob_sha"]==EXPECTED["GENERIC_ACTIVATION.json"]
assert generic["verification_git_blob_sha"]==EXPECTED["GENERIC_VERIFICATION.json"]
assert generic["projection_verification_path"]=="canonical/verification/TERMINAL_STRUCTURAL_PARALLELIZATION_ROOT_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
assert generic["status"]=="ACTIVE_IFF_EXACT_ROOT_PROJECTION_RECEIPT_EXISTS_AND_PASSES__GENERIC_CONDITIONAL_THEOREM_ONLY__ZERO_CREDIT"
assert generic["generic_conditional_adaptation_independence_proved"] is True
assert generic["current_benchmark_instantiation_receipts_proved"]==0
assert generic["benchmark_thin_adapter_still_required"] is True
assert generic["explicit_fresh_reality_authority_still_required"] is True
assert generic["execution_authority"] is False
assert generic["promotion_authority"] is False
assert generic["fresh_reality_authority"] is False
assert generic["acceptance_credit_delta"]==0

overlay=root["scheduler_policy"]["structural_breakthrough_overlay"]
assert overlay["precommit_isolation_theorem_status"]=="GENERIC_CONDITIONAL_THEOREM_INDEPENDENTLY_PROVED__ZERO_CURRENT_BENCHMARK_INSTANTIATIONS__THIN_ADAPTERS_AND_EXPLICIT_FRESH_REALITY_AUTHORITY_STILL_REQUIRED"
assert overlay["fresh_reality_authority"] is False

assert ga["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__GENERIC_CONDITIONAL_THEOREM_ONLY__ZERO_CREDIT"
assert ga["authority"]=={"generic_conditional_theorem":True,"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(v==0 for v in ga["accounting"].values())

assert gv["independent_runner"]["pull_request"]==1701
assert gv["independent_runner"]["verifier_merge_commit"]=="10594a02218613f703d692c49821a041f57e9d66"
assert gv["independent_runner"]["workflow_run_id"]==37180405038
assert gv["independent_runner"]["workflow_job_id"]==111371656849
assert gv["verified"]["generic_conditional_adaptation_independence_theorem"] is True
assert gv["verified"]["benchmark_comparability_separate"] is True
assert gv["verified"]["fresh_reality_authority"] is False
assert all(v==0 for v in gv["accounting"].values())

assert tv["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__26_PREDICATES__29_TYPED_OBLIGATIONS__ZERO_CREDIT"
assert tv["verified"]["unresolved_predicates"]==26
assert tv["verified"]["typed_obligations"]==29
assert tv["verified"]["comparator_strength_obligations"]==19
assert tv["verified"]["scope_completeness_obligations"]==10
assert tv["verified"]["relative_elo_absolute_nontransport_preserved"] is True
assert tv["verified"]["fresh_reality_block_preserved"] is True
assert tv["verified"]["acceptance_credit_authorized"] is False

print(json.dumps({
 "status":"PASS",
 "exact_root_blob":EXPECTED["ROOT.json"],
 "typed_obligations":29,
 "comparator_strength_obligations":19,
 "scope_completeness_obligations":10,
 "generic_conditional_isolation_proved":True,
 "benchmark_instantiations_proved":0,
 "fresh_reality_authority":False,
 "accepted_families":5,
 "proved_atomic":12,
 "unresolved_atomic":26,
 "acceptance_credit_delta":0,
},sort_keys=True))
