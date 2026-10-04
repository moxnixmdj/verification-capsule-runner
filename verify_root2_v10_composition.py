import json, pathlib, subprocess

P={
 "v10":"verification_inputs/root2_v10_composed.json",
 "fin":"verification_inputs/root2_v9_finance.json",
 "v8":"verification_inputs/root2_v8_parent.json",
 "omc":"verification_inputs/root2_v9_omc_alt.json",
}
H={
 "v10":"2012926814d0d06405da56da64e589b06fef1756",
 "fin":"ea5923e8a90ca115c8149266c4c37cc7e6c40a2a",
 "v8":"2eaeb74fe306ee2507145e26eb731f69f46e6153",
 "omc":"5894eb38bdb72e922bed2d1e54f16a38a7adec11",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in P.items():
    got=blob(p)
    assert got==H[k],(k,got,H[k])

load=lambda p: json.loads(pathlib.Path(p).read_text())
v10,fin,v8,omc=[load(P[k]) for k in ("v10","fin","v8","omc")]

assert v10["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10"
assert fin["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V9"
assert v10["exact_state"]==fin["exact_state"]==v8["exact_state"]
assert v10["accounting"]==fin["accounting"]
assert v10["execution_authority"] is False
assert v10["promotion_authority"] is False
assert v10["fresh_reality_authority"] is False

# Finance V9 must be preserved exactly as a prefix of semantic projection deltas.
assert len(v10["projection_deltas"])==len(fin["projection_deltas"])+1
assert v10["projection_deltas"][:-1]==fin["projection_deltas"]

# The one added delta must be exactly the independently verified OMC delta.
omc_delta=omc["projection_deltas"][-1]
assert v10["projection_deltas"][-1]==omc_delta
assert omc_delta["target"]=="CODING_TB4_GE_66_4"
assert "OMC_CLOUD" in omc_delta["to"]
assert omc_delta["deletion"]=="NO_PREDICATE_OR_ATTAINABILITY_CREDIT"

# Finance custom-route cut must remain intact.
assert "FINANCE_AGENT_V2_CUSTOM_ROUTE__COMPARABILITY_AND_VALS_PLATFORM_JURY_ZERO_SPEND_PROOF" not in v10["runnable_zero_reality"]
assert v10["finance_agent_v2_dual_route"]["custom_function"]["state"]=="DORMANT__PUBLIC_COMPARABILITY_ROUTE_SATURATED"
assert v10["finance_agent_v2_dual_route"]["default_shared_harness"]["state"].startswith("OPEN__")

# OMC must be added without reviving CircleCI or granting carrier credit.
providers={x["provider"] for x in v10["tb4_carrier_portfolio"]["candidates"]}
assert providers=={"Buildkite","OMC Cloud"}
deleted={x["provider"] for x in v10["tb4_carrier_portfolio"]["deleted"]}
assert "CircleCI" in deleted
assert v10["runnable_zero_reality"][0]=="TB4_OMC_CLOUD_ACCOUNT_RUNTIME_AND_ZERO_CASE_PREFLIGHT_WHEN_TRIAL_ACCESS_IS_AVAILABLE"
for fact in [
 "OMC_CLOUD_DOCKER_DOCKER_COMPOSE_NO_PAID_OVERAGE_AND_HARBOR_PROTOCOL_PREFLIGHT",
 "OMC_CLOUD_OBSERVED_NPROC_GE_8_USABLE_MEMORY_MB_GE_16384_FREE_STORAGE_MB_GE_51200",
 "OMC_CLOUD_TRIAL_ACCOUNT_AND_EXACT_8A16GB_OR_STRONGER_SHAPE_ACCESS",
]:
    assert fact in v10["waiting_external_facts"]

src=v10["source_bindings"]["tb4_omc_documentary_carrier"]
assert src["candidate_git_blob_sha"]=="b26e3c3cb46cca224aeef9de3d965f4507f72c5d"
assert src["activation_git_blob_sha"]=="a0e6d98e11decb237a3230dfe1c85d2929a4126d"
assert src["verification_git_blob_sha"]=="54c540c64e4615b02839122fb6a87136746ac322"

cp=v10["composition_provenance"]
assert cp["common_parent"]["git_blob_sha"]==H["v8"]
assert cp["finance_delta"]["child_blob_sha"]==H["fin"]
assert cp["omc_delta"]["independently_verified_alternate_child_blob_sha"]==H["omc"]
assert "ORTHOGONAL_DELTA_UNION_ONLY" in cp["rule"]

print("ROOT2_V10_COMPOSITION_PASS__FINANCE_V9_PLUS_OMC_ONLY__ZERO_CREDIT__NO_FRESH_REALITY")
