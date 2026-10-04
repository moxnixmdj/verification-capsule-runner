#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"subject/livebench_direct_authority_activation_v1"

def load(n): return json.loads((P/n).read_text(encoding="utf-8"))
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

EXPECTED={
 "activation.json":"08929577573866dc2bead65a19a856a6b4e152d2",
 "rebind_verification.json":"d62609ba2c100eb83a8c3fb057735ac67cab0129",
 "rebind_candidate.json":"8d43368368df6b2b38a4e2d3bb948c6456c4a6cb",
 "runtime_closure.json":"cabf49d6a6fa91639e76a3fe86a76a625a0f3bc1",
 "root.json":"e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59",
 "frontier_v17.json":"8c1325dd652b65a7d5c24e041ac06556a84f569c",
}
for n,w in EXPECTED.items():
    g=blob(P/n)
    assert g==w,(n,g,w)

a=load("activation.json")
v=load("rebind_verification.json")
c=load("rebind_candidate.json")
r=load("root.json")
f=load("frontier_v17.json")
cl=load("runtime_closure.json")
t="LIVEBENCH_IF_GE_65_7"

# Independent premise verification must already be a real merged public-runner pass.
assert v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
ir=v["independent_runner"]
assert ir["repository"]=="moxnixmdj/verification-capsule-runner"
assert ir["pull_request"]==1749
assert ir["merge_commit"]=="9d52562c57a669b112082d20bd61090bbcbc2c4b"
assert ir["workflow_run_id"]==37187197876
assert ir["workflow_job_id"]==111391551402
assert ir["conclusion"]=="success"
assert v["target_predicate"]==t
assert v["conditional_authority_if_exact_activation_verified"]["authorized_predicates"]==[t]
assert v["conditional_authority_if_exact_activation_verified"]["global_fresh_reality_authority"] is False
assert v["accounting"]["terminal_cases_consumed"]==0
assert v["execution_authority"] is False

# Current bound root still makes the target Root2-only.
part=r["current_residual_root_partition"]
assert t in part["root2_only"]
assert t not in part["root3_only"] and t not in part["root2_and_root3"]
assert part["unresolved_total"]==26

# Current frontier prefers direct scoped execution and shadow remains fallback only.
lb=f["livebench_if_isolation_route"]
assert lb["preferred_execution_strategy"]=="DIRECT_PREDICATE_LOCAL_FRESH_REALITY_AFTER_CURRENT_REBIND_VERIFICATION"
assert lb["shadow_route"]=="FALLBACK_ONLY"
assert lb["future_irreducible_result"]=="BRAIN_SCORE_GE_65_7_ON_FROZEN_200_CASE_2026_06_25_LIVEBENCH_IF_POPULATION"

# Frozen runtime closure had no case exposure and no external paid cognition.
probe=cl["independent_public_runtime_probe"]
assert probe["conclusion"]=="success"
assert probe["terminal_case_content_read"] is False
assert probe["terminal_cases_consumed"]==0
assert probe["model_dependency_count"]==0
assert probe["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert probe["paid_external_model_or_api_used"] is False
assert probe["incremental_spend_usd"]==0

# Authority firewall: exactly one predicate, local only, no credit or promotion.
assert a["schema"]=="PROJECT_BRAIN_LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V1"
assert a["active"] is True
assert a["target_predicate"]==t
assert a["authorized_predicates"]==[t]
sf=a["scope_firewall"]
assert sf["predicate_local_fresh_reality_authority"] is True
assert sf["global_fresh_reality_authority"] is False
assert sf["all_other_unresolved_predicates_authorized"] is False
assert sf["shadow_escrow_required"] is False
assert sf["shadow_one_use_claim_required"] is False
auth=a["authority"]
assert auth["execution"] is True
assert auth["predicate_local_fresh_reality"] is True
assert auth["global_fresh_reality"] is False
assert auth["promotion"] is False
assert auth["acceptance_credit"] is False
assert all(x==0 for x in a["accounting"].values())

# Exact route remains frozen and zero-spend.
e=a["exact_execution_binding"]
assert e["candidate_commit"]=="d5de4f5808dced840da34d051e3f9a5ff06e2e54"
assert e["candidate_tree"]=="fd39e966d4686c7317b9a1558b360eb0c58ad76f"
assert e["benchmark_id"]=="LIVEBENCH_IF_2026_06_25"
assert e["population_count"]==200
assert e["threshold_percent"]==65.7
assert e["paid_external_model_or_api_allowed"] is False
assert e["larger_or_paid_runner_allowed"] is False
assert e["allow_optional_model_planner"] is False
assert e["external_tools_allowed"] is False
assert e["required_cognition_dependency_class"]=="MODEL_INDEPENDENT"

required=set(a["point_of_use_gates_before_any_terminal_case_read"])
for gate in {
 "EXACT_PRECOMMITTED_COMPONENT_HASHES_UNCHANGED",
 "SAME_STANDARD_PUBLIC_RUNNER_CLASS",
 "SAME_RUNNER_ZERO_CASE_RESOURCE_AND_TRANSITIVE_DEPENDENCY_PREFLIGHT_PASS",
 "NO_PAID_EXTERNAL_MODEL_OR_API",
 "NO_CANDIDATE_MUTATION_AFTER_PRECOMMIT",
 "NO_ADAPTIVE_CASE_SELECTION",
 "NO_CASE_REPLACEMENT",
 "NO_TERMINAL_CASE_TUNING",
}:
    assert gate in required,gate

# Candidate itself never granted authority; activation is the narrow edge.
assert c["execution_authority"] is False
assert c["fresh_reality_authority"] is False
assert c["promotion_authority"] is False

print(json.dumps({
 "status":"INDEPENDENT_PUBLIC_PASS__LIVEBENCH_DIRECT_AUTHORITY_ACTIVATION_FIREWALL_VALID",
 "authorized_predicates":[t],
 "predicate_local_fresh_reality_authority":True,
 "global_fresh_reality_authority":False,
 "execution_authority":True,
 "promotion_authority":False,
 "acceptance_credit_delta":0,
 "terminal_cases_consumed":0
},sort_keys=True,indent=2))
