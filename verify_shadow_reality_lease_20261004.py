from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "lease_v1_20261004"
SHADOW = SUB / "shadow_reality_lease_v1.py"
GENERIC = SUB / "generic_precommit_isolation_theorem_v1.py"
POLICY = SUB / "SHADOW_REALITY_LEASE_POLICY_V1.json"

EXPECTED_SHADOW = "db7c77d21ce410c29754e029910d774c890e9780"
EXPECTED_GENERIC = "58f2ae9c3f0ef0ac55da2e58d0ed81ae88560296"
EXPECTED_POLICY = "55f749a0a586e0b178195b62b7dae154910f0cbc"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

assert git_blob_sha(SHADOW) == EXPECTED_SHADOW
assert git_blob_sha(GENERIC) == EXPECTED_GENERIC
assert git_blob_sha(POLICY) == EXPECTED_POLICY

canonical = types.ModuleType("canonical")
runtime_pkg = types.ModuleType("canonical.runtime")
canonical.runtime = runtime_pkg
sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime_pkg

spec_g = importlib.util.spec_from_file_location(
    "canonical.runtime.generic_precommit_isolation_theorem_v1", GENERIC
)
assert spec_g and spec_g.loader
g = importlib.util.module_from_spec(spec_g)
sys.modules[spec_g.name] = g
spec_g.loader.exec_module(g)

spec_s = importlib.util.spec_from_file_location(
    "canonical.runtime.shadow_reality_lease_v1", SHADOW
)
assert spec_s and spec_s.loader
s = importlib.util.module_from_spec(spec_s)
sys.modules[spec_s.name] = s
spec_s.loader.exec_module(s)

policy = json.loads(POLICY.read_text())
assert policy["execution_authority"] is False
assert policy["promotion_authority"] is False
assert policy["global_fresh_reality_authority"] is False
assert policy["shadow_collection_authority"] is False
assert policy["independent_verification_required"] is True
assert policy["separate_activation_required"] is True
assert policy["accounting"]["acceptance_credit_delta"] == 0
assert "NO_CLAIM_THIS_CANDIDATE_FILE_ITSELF_GRANTS_SHADOW_COLLECTION_AUTHORITY" in policy["hard_nonclaims"]

def isolation():
    r = {}
    for i,c in enumerate(("candidate","harness","scorer","environment","policy"), start=1):
        r[f"{c}_sha256"] = str(i) * 64
        r[f"observed_{c}_sha256"] = str(i) * 64
    r.update({
        "commit_event_sequence": 10,
        "case_reveal_event_sequence": 11,
        "execution_start_event_sequence": 12,
        "independent_executor": True,
        "committed_components_immutable": True,
        "no_case_or_evaluation_feedback_to_committed_components": True,
        "unrelated_work_cannot_mutate_committed_components": True,
        "outputs_bound_to_commitment": True,
        "observed_causal_edges": [
            ["case_content","execution_output"],
            ["evaluation_output","receipt_store"],
            ["unrelated_zero_reality_work","unrelated_artifact"],
        ],
    })
    r["commitment_sha256"] = g.commitment_digest(r)
    return r

def adapter():
    return {
        "population_identity_verified": True,
        "scorer_or_grader_equivalence_verified": True,
        "effort_and_context_semantics_verified": True,
        "tool_and_environment_boundary_verified": True,
        "exact_comparator_identity_verified": True,
        "no_proxy_substitution_verified": True,
        "zero_incremental_spend_or_entitlement_verified": True,
        "acceptance_rule_bound": True,
    }

def activation():
    return {
        "schema": s.AUTHORITY_SCHEMA,
        "active": True,
        "shadow_collection_authority": True,
        "independent_verification_pass": True,
        "zero_incremental_spend_only": True,
        "write_only_escrow_only": True,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authority": False,
        "promotion_authority": False,
    }

def lease():
    x = {
        "lease_id": "verify:benchmark:epoch-1",
        "benchmark_id": "LIVEBENCH_IF_GE_65_7",
        "candidate_sha256": "a"*64,
        "benchmark_contract_sha256": "b"*64,
        "population_manifest_sha256": "c"*64,
        "escrow_sink_contract_sha256": "d"*64,
        "one_use_nonce": "nonce-verify-001",
        "candidate_frozen": True,
        "candidate_mutation_blocked": True,
        "unrelated_work_mutation_blocked": True,
        "zero_incremental_spend_guard_pass": True,
        "independent_executor": True,
        "one_use_lease": True,
        "lease_consumed": False,
        "escrow_write_only": True,
        "result_read_blocked_until_zero_reality_fixed_point": True,
        "outputs_bound_to_lease": True,
        "result_visible_to_candidate": False,
        "result_visible_to_planner": False,
        "result_visible_to_zero_reality_work": False,
    }
    x["lease_digest_sha256"] = s.lease_digest(x)
    return x

good = s.verify_shadow_lease(lease(), isolation(), adapter(), activation())
assert good["shadow_collection_ready"] is True
assert good["shadow_collection_authority"] is True
assert good["global_fresh_reality_authority"] is False
assert good["acceptance_credit_authorized"] is False
assert good["promotion_authority"] is False
assert good["execution_authority_beyond_shadow_collection"] is False
assert good["result_visibility"] == "WRITE_ONLY_ESCROW"

a = activation(); a["independent_verification_pass"] = False
bad = s.verify_shadow_lease(lease(), isolation(), adapter(), a)
assert bad["shadow_collection_ready"] is False
assert "SHADOW_ACTIVATION_NOT_INDEPENDENTLY_VERIFIED" in bad["reasons"]

a = activation(); a["global_fresh_reality_authority"] = True
bad = s.verify_shadow_lease(lease(), isolation(), adapter(), a)
assert bad["shadow_collection_ready"] is False
assert "SHADOW_ACTIVATION_MUST_NOT_GRANT_GLOBAL_FRESH_REALITY" in bad["reasons"]

x = lease(); x["result_visible_to_candidate"] = True; x["lease_digest_sha256"] = s.lease_digest(x)
bad = s.verify_shadow_lease(x, isolation(), adapter(), activation())
assert bad["shadow_collection_ready"] is False

x = lease(); x["candidate_mutation_blocked"] = False; x["lease_digest_sha256"] = s.lease_digest(x)
bad = s.verify_shadow_lease(x, isolation(), adapter(), activation())
assert bad["shadow_collection_ready"] is False

ad = adapter(); ad["exact_comparator_identity_verified"] = False
bad = s.verify_shadow_lease(lease(), isolation(), ad, activation())
assert bad["shadow_collection_ready"] is False

iso = isolation(); iso["observed_candidate_sha256"] = "9"*64
bad = s.verify_shadow_lease(lease(), iso, adapter(), activation())
assert bad["shadow_collection_ready"] is False

x = lease(); x["lease_consumed"] = True; x["lease_digest_sha256"] = s.lease_digest(x)
bad = s.verify_shadow_lease(x, isolation(), adapter(), activation())
assert bad["shadow_collection_ready"] is False

post = s.classify_shadow_result_after_fixed_point(
    zero_reality_fixed_point_reached=True,
    shadow_lease_passed=True,
    route_still_required=True,
    output_bound_to_lease=True,
    independent_result_verification_pass=True,
)
assert post["eligible_for_predicate_specific_reduction"] is True
assert post["acceptance_credit_authorized"] is False
assert post["promotion_authority"] is False
assert post["global_fresh_reality_authority"] is False
assert post["separate_predicate_specific_activation_required"] is True

dom = s.classify_shadow_result_after_fixed_point(
    zero_reality_fixed_point_reached=True,
    shadow_lease_passed=True,
    route_still_required=False,
    output_bound_to_lease=True,
    independent_result_verification_pass=True,
)
assert dom["eligible_for_predicate_specific_reduction"] is False
assert dom["discard_as_dominated_or_stale"] is True

print(json.dumps({
    "status": "PASS",
    "shadow_runtime_git_blob_sha": EXPECTED_SHADOW,
    "generic_dependency_git_blob_sha": EXPECTED_GENERIC,
    "policy_git_blob_sha": EXPECTED_POLICY,
    "shadow_collection_ready_under_all_gates": True,
    "candidate_cannot_self_activate": True,
    "write_only_escrow_enforced": True,
    "candidate_mutation_blocked": True,
    "one_use_replay_blocked": True,
    "global_fresh_reality_authority": False,
    "acceptance_credit_authorized": False,
    "promotion_authority": False,
}, sort_keys=True))
