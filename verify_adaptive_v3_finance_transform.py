import json, pathlib, subprocess

FILES={
  "v2":"subject/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2.json",
  "v3":"subject/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V3.json",
  "finance_receipt":"subject/FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "finance_cut":"subject/FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_20261004_V1.json",
  "root":"subject/TERMINAL_ROOT_CAUSE_STATE_V1.json",
  "root2":"subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json",
  "root3":"subject/ROOT3_MINIMUM_ACTION_CUT_V2.json",
  "retrieval":"subject/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json",
}
EXPECTED={
  "v2":"c5b9a287b51c0594f7925770f0f22fbbbb2738dc",
  "v3":"b9decd9afa43a37b0d67da5148285d58483caaaa",
  "finance_receipt":"8aea6757479980c9f2e2538a4f2651ad23653c10",
  "finance_cut":"2a831b8632b18fe9e10ed423f131b6ae93d99b77",
  "root":"2c64185e39d7f5e8fe5773e420e0c1b9f56458e5",
  "root2":"2012926814d0d06405da56da64e589b06fef1756",
  "root3":"4d8ce78ebe312100bbfc524062199961c0c6479d",
  "retrieval":"55b1d411561f720fcd9d66c127cecd63ef0b5f5e",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

v2=json.loads(pathlib.Path(FILES["v2"]).read_text())
v3=json.loads(pathlib.Path(FILES["v3"]).read_text())
fr=json.loads(pathlib.Path(FILES["finance_receipt"]).read_text())
fc=json.loads(pathlib.Path(FILES["finance_cut"]).read_text())
root=json.loads(pathlib.Path(FILES["root"]).read_text())
r2=json.loads(pathlib.Path(FILES["root2"]).read_text())
r3=json.loads(pathlib.Path(FILES["root3"]).read_text())
retr=json.loads(pathlib.Path(FILES["retrieval"]).read_text())

assert v3["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V3"
assert v3["supersedes_if_verified"]=="canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2.json"
assert v3["compiled_from_main"]=="d8acbc0c04e38b57e2f870759c104af3ff0752c8"

# Truth and optimization semantics preserved.
for key in ["exact_live_state","verified_runtime","optimization","accounting","execution_authority","promotion_authority","fresh_reality_authority"]:
    assert v3[key]==v2[key],key
assert v3["exact_live_state"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
    "total_families":19,"total_atomic":38,"terminal":False,"root1_positive_gaps":0,
    "root2_only":16,"root3_only":7,"root2_and_root3":3
}

# Domain authorities preserved exactly, except rebinding the terminal-root-state snapshot to current V2-active root state.
assert v3["authority_bindings"]["root2"]==v2["authority_bindings"]["root2"]
assert v3["authority_bindings"]["root3"]==v2["authority_bindings"]["root3"]
assert v3["authority_bindings"]["retrieval"]==v2["authority_bindings"]["retrieval"]
assert v3["authority_bindings"]["terminal_root_state"]["path"]==v2["authority_bindings"]["terminal_root_state"]["path"]
assert v3["authority_bindings"]["terminal_root_state"]["git_blob_sha"]==EXPECTED["root"]

assert blob(FILES["root2"])==v3["authority_bindings"]["root2"]["frontier_git_blob_sha"]
assert blob(FILES["root3"])==v3["authority_bindings"]["root3"]["cut_git_blob_sha"]
assert blob(FILES["retrieval"])==v3["authority_bindings"]["retrieval"]["current_authority_git_blob_sha"]

# Finance source binding is exact and carries zero terminal credit.
fb=v3["authority_bindings"]["finance_index_public_transform_saturation"]
assert fb["subject_git_blob_sha"]==EXPECTED["finance_cut"]
assert fb["verification_git_blob_sha"]==EXPECTED["finance_receipt"]
assert fr["subject"]["git_blob_sha"]==EXPECTED["finance_cut"]
assert fr["verifier"]["workflow_run_id"]==37174229191
assert fr["verifier"]["workflow_job_id"]==111353390105
assert fr["verifier"]["conclusion"]=="success"
assert fr["verified"]["zero_floor_proved"] is False
assert fr["verified"]["predicate_closed"] is False
assert fc["exact_deduction"]["finance_subscore_zero_floor_proved"] is False
assert fc["exact_deduction"]["direct_threshold_predicate_closed"] is False

# Exactly three new deletion identities.
expected_new={
  "FINANCE_INDEX_REPEAT_GENERIC_PUBLIC_INNER_TRANSFORM_SEARCH",
  "FINANCE_INDEX_EXPECT_FREE_AA_API_COMPONENT_BENCHMARK_SCORES",
  "FINANCE_INDEX_DUPLICATE_AA_OWNER_OUTREACH_FOR_INDEX_OR_COMPONENT_SCORES",
}
assert set(v3["preserved_search_deletions"])-set(v2["preserved_search_deletions"])==expected_new
assert set(v2["preserved_search_deletions"]).issubset(v3["preserved_search_deletions"])

# Same action phases/actions; only retrieval anti-repeat rule may be strengthened.
assert [x["phase"] for x in v3["current_execution_policy"]]==[x["phase"] for x in v2["current_execution_policy"]]
assert [x["action"] for x in v3["current_execution_policy"]]==[x["action"] for x in v2["current_execution_policy"]]
for a,b in zip(v3["current_execution_policy"],v2["current_execution_policy"]):
    if a["action"]!="RUN_RETRIEVAL_V19_ONLY_FOR_NEW_LOAD_BEARING_STRONGER_PROOF_OR_MATERIAL_WAKE":
        assert a==b

# Hard rules only strengthen V2.
assert set(v2["hard_rules"]).issubset(v3["hard_rules"])
assert "FINANCE_INDEX_ZERO_FLOOR_REMAINS_UNPROVED__SEARCH_DELETION_MUST_NOT_BECOME_SCORE_OR_ACCEPTANCE_CREDIT" in v3["hard_rules"]
assert "REOPEN_FINANCE_PUBLIC_TRANSFORM_ROUTE_ONLY_ON_MATERIAL_PUBLIC_SCHEMA_OR_METHODOLOGY_CHANGE_OR_STRONGER_FORMAL_PROOF" in v3["hard_rules"]

# Current root state still says terminal false and Root3 fresh reality remains blocked.
assert root["current_acceptance"]["terminal"] is False
assert root["current_acceptance"]["accepted_families"]==5
assert root["current_acceptance"]["unresolved_atomic"]==26
assert r3["fresh_reality_authority"] is False
assert v3["fresh_reality_authority"] is False

print("ADAPTIVE_V3_FINANCE_TRANSFORM_SEARCH_DELETION_PASS__V2_SEMANTICS_PRESERVED__ZERO_CREDIT")
