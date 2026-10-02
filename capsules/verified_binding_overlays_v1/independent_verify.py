import hashlib, json
from pathlib import Path
from canonical.runtime.protocol_implication_overlay_batch_reducer_v1 import reduce_with_overlays

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json":"e627c2c1d9aa70cf6be42b40e249f4a5bfb9e64d",
"canonical/runtime/protocol_implication_overlay_batch_reducer_v1.py":"a3d3cd421f5e9439283b0e127bda0876d17c3561",
"canonical/tests/test_protocol_implication_overlay_batch_reducer_v1.py":"27903778997b627a1566953a0b45ebef73f9df05",
"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json":"0910ce3a2351fc439e03a1fa2ae708fb3c6463ef",
"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json":"45e1a4eaa2214c4a92f5d5787695069f2fe48aaf",
"canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"9dab3da99dda356a4ac56212899fc787e9ec4a5a",
"canonical/runtime/protocol_implication_batch_reducer_v1.py":"2c4fff73dc18fd85b1f7759ff1b8e3c55906af32",
"canonical/runtime/protocol_implication_scope_algebra_v2.py":"6aba64c26433b4a8646d5d96bb07e5ba5b46ca1b",
"canonical/runtime/witness_target_binding_totalizer_v1.py":"9f13232826612b2248274f3e13147767b7c7c8f5",
"canonical/governance/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_INPUT_V2.json":"4e5b944c86b8745083cc9d97fe186aa4b1322747",
"canonical/verification/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json":"c9a3046dd5a409379d675051861600919c3017fb",
"canonical/verification/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_INDEPENDENT_FAILURE_20261002_V1.json":"f2c8741a9249b4ad0ae4a82b1ac3f061c882e3e0"
}

def blob(rel):
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

for rel,exp in EXPECTED.items():
    assert blob(rel)==exp,(rel,blob(rel),exp)

def load(rel): return json.loads((ROOT/rel).read_text())
out=reduce_with_overlays(
    load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"),
    load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"),
    load("canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
    load("canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json"),
    root=ROOT)

assert out["status"].startswith("PASS"),out
assert out["target_count"]==11,out
assert out["base_pair_count"]==99,out
assert out["verified_overlay_pair_count"]==1,out
assert out["total_pair_count"]==100,out
assert out["improved_target_count"]==1,out
assert out["closed_target_count"]==0,out
rows={x["predicate_id"]:x for x in out["target_results"]}
s=rows["SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
assert s["best_current_source_kind"]=="VERIFIED_OVERLAY",s
assert s["current_best_hole_score"]==[1,1,2],s
assert s["best_current_scope_relation_missing"] is True,s
assert s["best_current_missing_atoms"]==["metric:matched_quality"],s
assert s["best_current_failed_metrics"]==["matched_quality_noninferiority","required_claim_coverage_noninferiority"],s
assert out["acceptance_credit_delta"]==0 and out["family_credit_delta"]==0
assert out["execution_authority"] is False and out["promotion_authority"] is False
print("independent verified binding overlay check: PASS")
