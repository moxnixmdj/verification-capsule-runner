#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"subject/livebench_direct_rebind_v2"

def load(name):
    return json.loads((P/name).read_text(encoding="utf-8"))

def git_blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

EXPECTED={
 "root.json":"e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59",
 "frontier_v17.json":"8c1325dd652b65a7d5c24e041ac06556a84f569c",
 "predicate_registry.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "precommit_v2.json":"66554061f204d8a86b37a30c84d0cf07a525a786",
 "thin_adapter_activation.json":"04505bc3fca23c448b35cd5ad546bac770f5cb34",
 "carrier.json":"093ec45bd3889fc3a8edd4f50f41c93a9de2cd10",
 "runtime_closure_binding.json":"cabf49d6a6fa91639e76a3fe86a76a625a0f3bc1",
 "rebind_candidate_v2.json":"8d43368368df6b2b38a4e2d3bb948c6456c4a6cb",
 "frozen/astra_runtime.py":"7f5d16b1db69cb620954bc778e0ba6e15e687b75",
 "frozen/root2_livebench_if_astra_inference_adapter_v1.py":"7e3885fa7a6e56df656c066e0a8f17cfa21424e7",
 "frozen/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
 "frozen/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
 "frozen/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
 "frozen/BOUND_CAPABILITY_REGISTRY_V1.json":"7badee4878700f2cd4176beb8319d2a6a0bdf782"
}
for rel,want in EXPECTED.items():
    got=git_blob(P/rel)
    assert got==want,(rel,got,want)

root=load("root.json"); front=load("frontier_v17.json")
pre=load("precommit_v2.json"); thin=load("thin_adapter_activation.json")
carrier=load("carrier.json"); closure=load("runtime_closure_binding.json")
cand=load("rebind_candidate_v2.json")
target="LIVEBENCH_IF_GE_65_7"

part=root["current_residual_root_partition"]
assert target in part["root2_only"]
assert target not in part["root3_only"] and target not in part["root2_and_root3"]
assert part["unresolved_total"]==26

assert pre["target_predicate"]==target
assert pre["candidate"]["commit"]=="d5de4f5808dced840da34d051e3f9a5ff06e2e54"
assert pre["candidate"]["tree"]=="fd39e966d4686c7317b9a1558b360eb0c58ad76f"
assert pre["scorer"]["population_count"]==200
assert pre["scorer"]["threshold_percent"]==65.7
assert pre["scorer"]["dataset_revision"]=="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
assert pre["policy"]["benchmark_id"]=="LIVEBENCH_IF_2026_06_25"
assert pre["policy"]["allow_optional_model_planner"] is False
assert pre["policy"]["external_tools_allowed"] is False
assert pre["policy"]["required_cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert pre["case_exposure"]["terminal_case_content_read"] is False
assert pre["case_exposure"]["terminal_cases_consumed"]==0

eff=thin["effect"]
assert eff["thin_adapter_gate_complete"] is True
assert eff["thin_adapter_fields_proved"]==eff["thin_adapter_fields_required"]==8
for k in (
 "population_identity_verified","scorer_or_grader_equivalence_verified",
 "effort_and_context_semantics_verified","tool_and_environment_boundary_verified",
 "exact_comparator_identity_verified","no_proxy_substitution_verified",
 "zero_incremental_spend_or_entitlement_verified","acceptance_rule_bound"
):
    assert eff[k] is True,k

bind=carrier["execution_binding"]
assert bind["repository_visibility_required"]=="public"
assert bind["runner_label"]=="ubuntu-24.04"
assert bind["runner_class"]=="STANDARD_GITHUB_HOSTED"
assert bind["larger_or_paid_runner_allowed"] is False
assert bind["paid_external_model_or_api_allowed"] is False

probe=closure["independent_public_runtime_probe"]
assert probe["conclusion"]=="success"
assert probe["observed_status"]=="PASS__EXACT_BLOBS_SYNTHETIC_FULL_ADAPTER_PATH__PUBLIC_GITHUB_RUNNER"
assert probe["result_status"]=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE"
assert probe["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert probe["model_dependency_count"]==0
assert probe["terminal_case_content_read"] is False
assert probe["terminal_cases_consumed"]==0
assert probe["fresh_reality_consumed"] is False
assert probe["paid_external_model_or_api_used"] is False
assert probe["incremental_spend_usd"]==0
fb=closure["frozen_identity_binding"]
assert fb["frozen_candidate_commit_match"] is True
assert fb["all_public_probe_runtime_blobs_equal_frozen_candidate_commit_blobs"] is True
assert fb["exact_transitive_runtime_dependency_closure_proved_by_successful_execution_and_content_identities"] is True

lb=front["livebench_if_isolation_route"]
assert lb["preferred_execution_strategy"]=="DIRECT_PREDICATE_LOCAL_FRESH_REALITY_AFTER_CURRENT_REBIND_VERIFICATION"
assert lb["shadow_route"]=="FALLBACK_ONLY"
assert lb["shadow_escrow"]=="NOT_ON_INCUMBENT_CRITICAL_PATH_WHILE_DIRECT_REBIND_REMAINS_ADMISSIBLE"
rem=set(lb["remaining_zero_reality"])
expected_rem={
 "EXACT_TRANSITIVE_FROZEN_RUNTIME_DEPENDENCY_CLOSURE_OR_FORMALLY_PROVED_EQUIVALENT_SUBTREE_AND_SAME_SYNTHETIC_ZERO_CASE_INFERENCE_PASS",
 "CURRENT_STATE_PREDICATE_LOCAL_DIRECT_AUTHORITY_REBIND_INDEPENDENT_VERIFICATION_AFTER_RUNTIME_PASS"
}
assert rem==expected_rem,rem
assert rem-{"EXACT_TRANSITIVE_FROZEN_RUNTIME_DEPENDENCY_CLOSURE_OR_FORMALLY_PROVED_EQUIVALENT_SUBTREE_AND_SAME_SYNTHETIC_ZERO_CASE_INFERENCE_PASS"}=={
 "CURRENT_STATE_PREDICATE_LOCAL_DIRECT_AUTHORITY_REBIND_INDEPENDENT_VERIFICATION_AFTER_RUNTIME_PASS"
}
assert lb["future_irreducible_result"]=="BRAIN_SCORE_GE_65_7_ON_FROZEN_200_CASE_2026_06_25_LIVEBENCH_IF_POPULATION"
assert lb["fresh_reality_authority"] is False

assert cand["target_predicate"]==target
ce=cand["conditional_effect_if_independently_verified"]
assert ce["predicate_local_fresh_reality_authority"] is True
assert ce["authorized_predicates"]==[target]
assert ce["global_fresh_reality_authority"] is False
assert ce["all_other_unresolved_predicates_unauthorized"] is True
assert cand["execution_authority"] is False
assert cand["fresh_reality_authority"] is False
assert cand["promotion_authority"] is False
assert all(v==0 for v in cand["accounting"].values())
assert all(v==0 for v in closure["accounting"].values())

hist=cand["historical_theorem_chain"]
assert hist["theorem"]["pr"]==1436
assert hist["theorem"]["workflow_run_id"]==37158244145
assert hist["proved_rule"]=="PREDICATE_LOCAL_ZERO_REALITY_CONE_COMMUTATIVITY_FOR_ROOT2_ONLY_BRAIN_SCORE_ONLY_PREDICATES"
assert hist["symbolic"]=="Deps0(p)∩Pending0=∅ => Reduce_p(Score_p,Z_pending)=Reduce_p(Score_p)"

print(json.dumps({
 "status":"INDEPENDENT_PUBLIC_PASS__CURRENT_LIVEBENCH_PREDICATE_LOCAL_DIRECT_AUTHORITY_REBIND_PREMISES_PROVED",
 "target_predicate":target,
 "authorized_predicates_if_activated":[target],
 "global_fresh_reality_authority":False,
 "shadow_route_required":False,
 "acceptance_credit_delta":0,
 "terminal_cases_consumed":0
},sort_keys=True,indent=2))
