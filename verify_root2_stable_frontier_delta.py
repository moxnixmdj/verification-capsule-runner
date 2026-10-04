import hashlib,json,pathlib
B="capsules/root2_stable_frontier_delta_20261004"
P={
 "delta":f"{B}/ROOT2_CLOSURE_V2_STABLE_FRONTIER_DELTA_20261004_V1.json",
 "base":f"{B}/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V1.json",
 "carrier":f"{B}/TB4_BUILDKITE_ALL_ACCESS_TRIAL_CARRIER_CANDIDATE_20261004_V1.json",
 "synth":f"{B}/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json",
}
E={"delta":"3707492c4a76b7ca6874974ca327b1aaba844eec","base":"a58aa3513449ec5e56f66204fd33f3916d1bc09c","carrier":"2725cf6820fb7ce6025213d474b9acf2937282ee","synth":"f2ef80facb39264b1e12b81e451eb4499a3b987f"}
def blob(p):
 b=pathlib.Path(p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,p in P.items(): assert blob(p)==E[k],(k,blob(p),E[k])
d={k:json.loads(pathlib.Path(p).read_text()) for k,p in P.items()}
assert d["delta"]["base_frontier"]["git_blob_sha"]==E["base"]
assert d["delta"]["base_frontier"]["status_required"]==d["base"]["status"]
ds={x["id"]:x for x in d["delta"]["deltas"]}
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
assert d["delta"]["accounting"]["incremental_spend_usd"]==0
assert d["delta"]["accounting"]["terminal_cases_consumed"]==0
assert d["delta"]["execution_authority"] is False
assert d["delta"]["promotion_authority"] is False
assert d["delta"]["fresh_reality_authority"] is False
print("ROOT2_STABLE_FRONTIER_DELTA_INDEPENDENT_PASS__EXACT_4_BLOB_CHAIN__ZERO_CREDIT")
