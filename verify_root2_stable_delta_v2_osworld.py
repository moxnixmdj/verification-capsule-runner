import hashlib,json,pathlib
B="capsules/root2_stable_delta_v2_osworld_20261004"
P={
"delta":f"{B}/ROOT2_CLOSURE_V2_STABLE_FRONTIER_DELTA_20261004_V1.json",
"base":f"{B}/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V1.json",
"carrier":f"{B}/TB4_BUILDKITE_ALL_ACCESS_TRIAL_CARRIER_CANDIDATE_20261004_V1.json",
"synth":f"{B}/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json",
"oswRec":f"{B}/OSWORLD_V21_GITLAB_PROTOCOL_RECONCILIATION_V1.json",
"oswVer":f"{B}/OSWORLD_V21_GITLAB_PROTOCOL_THEOREM_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}
E={
"delta":"2cebd60adaf7edd6f35081806eea856c96d05486",
"base":"a58aa3513449ec5e56f66204fd33f3916d1bc09c",
"carrier":"2725cf6820fb7ce6025213d474b9acf2937282ee",
"synth":"f2ef80facb39264b1e12b81e451eb4499a3b987f",
"oswRec":"a6142a898df97c8d9691b6a810850fa8c962b035",
"oswVer":"12fa87058ba2d7a599f8f410ba99598efd1dff8e",
}
def blob(p):
    b=pathlib.Path(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,p in P.items():
    got=blob(p)
    assert got==E[k],(k,got,E[k])
d={k:json.loads(pathlib.Path(p).read_text()) for k,p in P.items()}
delta=d["delta"]
assert delta["base_frontier"]["git_blob_sha"]==E["base"]
assert delta["base_frontier"]["status_required"]==d["base"]["status"]
ds={x["id"]:x for x in delta["deltas"]}
assert set(ds)=={
 "SYNTHESIS_REQUIRED_CLAIM_COVERAGE_DELETE",
 "TB4_BUILDKITE_NAMED_MATERIAL_WAKE",
 "OSWORLD_GITLAB_EXACT_REVISION_DELETE"
}
s=ds["SYNTHESIS_REQUIRED_CLAIM_COVERAGE_DELETE"]
assert s["proof"]["candidate_git_blob_sha"]==E["synth"]
assert s["remaining_exact_residuals"]==["metric:matched_quality","matched_quality_noninferiority"]
assert d["synth"]["derived_metric_bounds"]["required_claim_coverage_noninferiority"]["lower"]==0
assert set(d["synth"]["explicitly_not_proved"])=={"metric:matched_quality","matched_quality_noninferiority"}
t=ds["TB4_BUILDKITE_NAMED_MATERIAL_WAKE"]
assert t["carrier_candidate"]["git_blob_sha"]==E["carrier"]
assert t["carrier_candidate"]["conclusion"]=="success"
assert t["carrier_admissibility"] is False
assert d["carrier"]["narrow_conclusion"]["tb4_carrier_admissibility_proved"] is False
o=ds["OSWORLD_GITLAB_EXACT_REVISION_DELETE"]
assert o["proof"]["reconciliation_git_blob_sha"]==E["oswRec"]
assert o["proof"]["verification_git_blob_sha"]==E["oswVer"]
assert o["proof"]["conclusion"]=="success"
assert o["replace_with"]=="GITLAB_FUNCTIONAL_PROTOCOL_PREFLIGHT"
ov=d["oswVer"]
assert ov["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert ov["subject"]["git_blob_sha"]==E["oswRec"]
assert ov["independent_runner"]["pull_request"]==1497
assert ov["independent_runner"]["workflow_run_id"]==37163196069
assert ov["independent_runner"]["workflow_job_id"]==111320730605
assert ov["independent_runner"]["conclusion"]=="success"
assert ov["verified"]["gitlab_absent_from_release_components"] is True
assert ov["verified"]["gitlab_success_contract_is_reachability_plus_valid_token"] is True
assert ov["verified"]["public_eval_guide_requires_url_and_token_without_revision"] is True
assert "DELETE_EXACT_TASK_WEB_GITLAB_REVISION" in ov["consequence"]
assert delta["accounting"]["incremental_spend_usd"]==0
assert delta["accounting"]["terminal_cases_consumed"]==0
assert delta["execution_authority"] is False
assert delta["promotion_authority"] is False
assert delta["fresh_reality_authority"] is False
print("ROOT2_STABLE_DELTA_V2_OSWORLD_INDEPENDENT_PASS__EXACT_6_BLOB_CHAIN__ZERO_CREDIT")
