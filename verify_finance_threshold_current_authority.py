import copy
import json
import pathlib
import subprocess

FILES = {
    "pauth": "subject/PROJECTED_CURRENT_TERMINAL_AUTHORITY_V1.json",
    "pbridge": "subject/PROJECTED_ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json",
    "proot": "subject/PROJECTED_TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "bauth": "subject/BASE_CURRENT_TERMINAL_AUTHORITY_V1.json",
    "bbridge": "subject/BASE_ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json",
    "broot": "subject/BASE_TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "activation": "subject/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_V1.json",
    "verification": "subject/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "theorem": "subject/FINANCE_INDEX_DIRECT_THRESHOLD_THEOREM_V1.json",
}
EXPECTED = {
    "pauth": "d696b1618dbe80ad05aec71dee0db2413540f174",
    "pbridge": "57f7d58bd76c12a4305d200bc83e5e521c33a4f0",
    "proot": "e3158715298c499fd1fb9a6e8da41681f0a58a89",
    "bauth": "65b3697d106dc0f96e13b5f92c421ca5da2123f8",
    "bbridge": "c5c475e11a578bf7bd4236583e74dd10359ac2f9",
    "broot": "d2e1827a40e1e547f17b61913f7c66f1ebce634c",
    "activation": "9b9d4a41d19a5e58e8967027e1d1837790287dc2",
    "verification": "f7c1127834aee3c70dc4634e8273e3a887e45c66",
    "theorem": "37f47143f62fe2f59e56d8eca4a64bae18a1ce8b",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

J={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
pa,pb,pr=J["pauth"],J["pbridge"],J["proot"]
ba,bb,br=J["bauth"],J["bbridge"],J["broot"]
act,ver,th=J["activation"],J["verification"],J["theorem"]

# Immutable terminal accounting and root partition.
assert pr["current_acceptance"]==br["current_acceptance"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
    "total_families":19,"total_atomic":38,"terminal":False,
}
assert pr["current_residual_root_partition"]==br["current_residual_root_partition"]
assert pr["accounting"]==br["accounting"]
assert pa["truth"]==ba["truth"]
assert pa["ownership_state"]==ba["ownership_state"]

# Exact finance authority subject.
assert act["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert act["subject"]["theorem_git_blob_sha"]==EXPECTED["theorem"]
assert ver["subject"]["activation_git_blob_sha"]==EXPECTED["activation"]
assert ver["independent_runner"]["pull_request"]==1598
assert ver["independent_runner"]["verifier_merge_commit"]=="26f2bc1848cd31b6d0733a604c6c68ceeecbecea"
assert ver["independent_runner"]["workflow_run_id"]==37169651931
assert ver["independent_runner"]["workflow_job_id"]==111339818067
assert ver["independent_runner"]["conclusion"]=="success"
assert th["theorem"]=="IF_VERIFIED_NORMALIZED_BRAIN_LOWER_BOUNDS_L_i_SATISFY_SUM_i(w_i*L_i)>=61_THEN_FINANCE_ACCOUNTING_INDEX_GE_61"

EXPECTED_OVERLAY = {
    "activation_path":"canonical/governance/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_V1.json",
    "activation_git_blob_sha":EXPECTED["activation"],
    "verification_path":"canonical/verification/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "verification_git_blob_sha":EXPECTED["verification"],
}

# Terminal-authority source overlay.
ao=pa["sources"]["finance_index_direct_threshold_overlay"]
assert ao["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert ao["activation_path"]==EXPECTED_OVERLAY["activation_path"]
assert ao["activation_git_blob_sha"]==EXPECTED["activation"]
assert ao["activation_verification_path"]==EXPECTED_OVERLAY["verification_path"]
assert ao["activation_verification_git_blob_sha"]==EXPECTED["verification"]
assert ao["theorem_git_blob_sha"]==EXPECTED["theorem"]
assert ao["effective_scheduling_authority"] is True
assert ao["supersedes_v5_action_for_target"]=="FINANCE_COMPONENTWISE_PREMISES_AND_NORMALIZATION_AGGREGATION"
assert ao["replacement_action"]=="MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert ao["fresh_reality_authority"] is False

# Root2 bridge overlay.
bo=pb["root2_closure_controller_v2"]["predicate_overlays"]["FINANCE_ACCOUNTING_INDEX_GE_61"]
for k,v in EXPECTED_OVERLAY.items():
    assert bo[k]==v
assert bo["effective_scheduling_authority"] is True
assert bo["supersedes_frontier_action"]=="FINANCE_COMPONENTWISE_PREMISES_AND_NORMALIZATION_AGGREGATION"
assert bo["replacement_action"]=="MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert bo["fresh_reality_authority"] is False

# Root-cause-state overlay.
ro=pr["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["predicate_overlays"]["FINANCE_ACCOUNTING_INDEX_GE_61"]
for k,v in EXPECTED_OVERLAY.items():
    assert ro[k]==v
assert ro["effective_scheduling_authority"] is True
assert ro["supersedes_frontier_action"]=="FINANCE_COMPONENTWISE_PREMISES_AND_NORMALIZATION_AGGREGATION"
assert ro["replacement_action"]=="MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert ro["fresh_reality_authority"] is False
assert pr["scheduler_policy"]["finance_index_direct_threshold_overlay_active"] is True
assert pr["scheduler_policy"]["finance_index_direct_threshold_route"]=="MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert pr["scheduler_policy"]["fresh_reality_before_zero_reality_fixed_point"] is False

# Prove that no other semantic JSON state changed.
ca=copy.deepcopy(pa)
del ca["sources"]["finance_index_direct_threshold_overlay"]
ca["next_terminal_action"]=ba["next_terminal_action"]
assert ca==ba

cb=copy.deepcopy(pb)
del cb["root2_closure_controller_v2"]["predicate_overlays"]
cb["next"]=bb["next"]
assert cb==bb

cr=copy.deepcopy(pr)
del cr["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["predicate_overlays"]
del cr["scheduler_policy"]["finance_index_direct_threshold_overlay_active"]
del cr["scheduler_policy"]["finance_index_direct_threshold_route"]
assert cr==br

# No authority escalation outside scheduling.
assert act["authority"]["execution_authority"] is False
assert act["authority"]["promotion_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False
assert ver["execution_authority"] is False
assert ver["promotion_authority"] is False
assert ver["fresh_reality_authority"] is False

print("PASS: Finance direct-threshold current-authority projection changes only the intended predicate-local scheduling overlay")
print("PASS: terminal accounting remains 5/19 families, 12/38 predicates, 26 unresolved")
print("PASS: Root2 V5 remains immutable; only FINANCE_ACCOUNTING_INDEX_GE_61 action is superseded")
print("PASS: no execution, promotion, acceptance, ownership, or fresh-reality authority added")
