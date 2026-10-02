from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path("capsules/p1_t0_t2_multiplex")
EXPECTED={
    "P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"0a98176de7e26c9a505d0a9045a0a8b1d08980be",
    "TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json":"8b439403a05b4a912f06a8866db25f6e53b52473",
    "TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"c571023e8b126c558f3995b2b0d348a7fbd084a0",
}
def blob(p:Path)->str:
    return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
for name,sha in EXPECTED.items():
    got=blob(ROOT/name)
    assert got==sha,(name,got,sha)

b=json.loads((ROOT/"P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json").read_text())
m=json.loads((ROOT/"TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json").read_text())
r=json.loads((ROOT/"TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json").read_text())

assert b["behavior_id"]=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
assert b["proof_mode"]=="T0_T2_MULTIPLEXED_DETERMINISTIC_INTERVENTION_RESCUE_GATE"
assert set(b["portfolio_bindings"])=={"T0","T2"}
expected={
 "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
assert set(b["direct_surface_bindings"])==expected
for portfolio,surface in [("T0","FRONTIERCODE_V1_1"),("T0","CURSORBENCH_4_0"),("T2","RECOVERY_SCOPE_COMPOSITION")]:
    rows=m["portfolios"][portfolio]["surfaces"]
    row=next(x for x in rows if x.get("id")==surface)
    assert "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF" in row.get("proof_routes",[])

forbidden={
 "HIDDEN_CAUSE_LABEL","REFERENCE_REPAIR_TARGET","HIDDEN_INTERVENTION_OR_RESCUE_RESULT",
 "GOLD_CAUSAL_EQUIVALENCE_CLASS","MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
 "POST_FREEZE_CASE_SELECTION_INFORMATION"
}
assert not (set(b["candidate_visible_information"]) & forbidden)
assert forbidden <= set(b["candidate_must_not_receive"])
checks=set(b["evaluator"]["required_checks"])
for req in [
 "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
 "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
 "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
 "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
 "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
]:
    assert req in checks
mut=set(b["evaluator"]["required_mutations"])
for req in ["SELECT_DOWNSTREAM_SYMPTOM","REPAIR_TARGET_WITH_NO_RESCUE","FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE","DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN"]:
    assert req in mut
ta=b["terminal_acceptance"]
assert ta["prewave_binding_is_terminal_result"] is False
assert ta["standalone_synthetic_whole_domain_score_forbidden"] is True
assert ta["no_exact_opus_case_level_comparator_required_for_prewave_admission"] is True
assert ta["any_load_bearing_p1_failure_blocks_behavior_proof"] is True
assert b["scope_accounting"]["no_scope_inheritance"] is True
for key in ["post_freeze_case_specific_tuning","case_replacement","result_to_runtime_feedback_during_wave","evaluator_or_threshold_edit_after_first_terminal_result","terminal_case_selection_before_route_freeze"]:
    assert b["contamination"][key] is False
assert b["prewave_admissible"] is False
assert b["independent_verification"] is None
assert b["execution_authority"] is False
assert b["terminal_results_observed"]==0
assert b["fresh_terminal_evidence_consumed"]==0

assert r["behavior_id"]=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
assert r["status"].startswith("INDEPENDENT_PASS__")
assert r["workflow_conclusion"]=="success"
assert r["result"]=={"case_count":1024,"failed":0}
assert r["terminal_results_observed"]==0
assert r["capability_credit_delta"]==0
assert "canonical/verification/TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json" in b["authority"]

print(json.dumps({
 "status":"INDEPENDENT_P1_MULTIPLEX_BINDING_PASS",
 "binding_blob":EXPECTED["P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"],
 "surface_bindings":sorted(expected),
 "prior_candidate_proof_receipt_run":r["workflow_run_id"],
 "terminal_results_observed":0,
 "capability_credit_delta":0
},sort_keys=True))
