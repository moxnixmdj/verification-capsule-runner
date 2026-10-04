import json, pathlib, subprocess

FILES={
  "activation":"subject/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_V1.json",
  "theorem":"subject/FINANCE_INDEX_DIRECT_THRESHOLD_THEOREM_V1.json",
  "receipt":"subject/FINANCE_INDEX_DIRECT_THRESHOLD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "residual":"subject/FINANCE_INDEX_COMPONENTWISE_RESIDUAL_VECTOR_V1.json",
  "v5":"subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json",
  "root":"subject/TERMINAL_ROOT_CAUSE_STATE_V1.json",
}
EXPECTED={
  "activation":"9b9d4a41d19a5e58e8967027e1d1837790287dc2",
  "theorem":"37f47143f62fe2f59e56d8eca4a64bae18a1ce8b",
  "receipt":"d138989a38fadba75e7dc538a80a34201c97ed04",
  "residual":"1f8b7ebd377ba06548d46399f62ed883c49dc0c3",
  "v5":"e948022f0a4e8d91b949a5155d850d56aa137c87",
  "root":"d2e1827a40e1e547f17b61913f7c66f1ebce634c",
}
def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

activation=json.loads(pathlib.Path(FILES["activation"]).read_text())
theorem=json.loads(pathlib.Path(FILES["theorem"]).read_text())
receipt=json.loads(pathlib.Path(FILES["receipt"]).read_text())
residual=json.loads(pathlib.Path(FILES["residual"]).read_text())
v5=json.loads(pathlib.Path(FILES["v5"]).read_text())
root=json.loads(pathlib.Path(FILES["root"]).read_text())

assert activation["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert activation["subject"]["theorem_git_blob_sha"]==EXPECTED["theorem"]
assert activation["subject"]["residual_git_blob_sha"]==EXPECTED["residual"]
assert activation["subject"]["verification_git_blob_sha"]==EXPECTED["receipt"]

assert receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert receipt["independent_runner"]["pull_request"]==1589
assert receipt["independent_runner"]["merge_commit"]=="bc6bf312480a3b669a7ba417c28daec912bc14a5"
assert receipt["independent_runner"]["workflow_run_id"]==37169346229
assert receipt["independent_runner"]["workflow_job_id"]==111338926561
assert receipt["independent_runner"]["conclusion"]=="success"
assert receipt["verified"]["direct_weighted_lower_bound_ge_61_is_sufficient"] is True
assert receipt["verified"]["componentwise_opus_noninferiority_required"] is False
assert receipt["verified"]["compensation_across_components_allowed"] is True

effect=activation["scheduling_effect"]
assert effect["old_required_route"]=="ALL_SIX_COMPONENTS_INDEPENDENTLY_PROVED_GE_FROZEN_OPUS55_COMPONENTS_WITH_EXACT_NORMALIZATION"
assert effect["new_primary_route"]=="MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert effect["componentwise_opus_noninferiority"]=="RETAIN_AS_SUFFICIENT_FALLBACK_NOT_MANDATORY"
assert effect["exact_rule"]=="SUM_i(w_i*VERIFIED_BRAIN_LOWER_BOUND_i)>=61"
assert effect["exact_six_bounds_required_unless_separate_verified_floor_replaces_component"] is True
assert effect["default_component_floors_allowed"] is False
assert effect["separate_index_run_required"] is False

assert theorem["componentwise_opus_noninferiority"]=="SUFFICIENT_BUT_NOT_NECESSARY"
assert theorem["compensation_across_components_allowed"] is True
assert residual["direct_threshold_shortcut"]["status"]=="CANDIDATE__INDEPENDENT_VERIFICATION_REQUIRED"

# Confirm this activation overlays exactly the current V5 Finance scheduling edge.
assert "FINANCE_COMPONENTWISE_PREMISES_AND_NORMALIZATION_AGGREGATION" in v5["runnable_zero_reality"]
assert "FINANCE_ACCOUNTING_INDEX_GE_61" in root["current_residual_root_partition"]["root2_only"]
assert root["current_acceptance"]=={
  "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
  "total_families":19,"total_atomic":38,"terminal":False
}

# Activation remains inert until current authority explicitly binds it.
assert activation["activation_condition"]=="MERGED_CURRENT_MAIN_AND_CURRENT_ROOT2_AUTHORITY_EXPLICITLY_BINDS_THIS_ACTIVATION"
assert activation["authority"]=={
  "scheduling_authority":False,
  "execution_authority":False,
  "promotion_authority":False,
  "fresh_reality_authority":False,
}

for obj in (activation,receipt,theorem,residual):
    if "accounting" in obj:
        for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed",
                  "acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            assert obj["accounting"][k]==0,(obj["schema"],k)
    else:
        assert obj["acceptance_credit_delta"]==0
        assert obj["incremental_spend_usd"]==0
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False

print("PASS: Finance direct-threshold activation is a scheduling-only, zero-credit overlay")
print("PASS: current V5 all-six componentwise route is safely weakened to weighted-deficit minimization")
print("PASS: default component floors remain forbidden; future lower-bound receipts remain external premises")
print("PASS: terminal state remains 5/19 families, 12/38 predicates, 26 unresolved")
