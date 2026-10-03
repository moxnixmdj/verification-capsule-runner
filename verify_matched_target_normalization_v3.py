#!/usr/bin/env python3
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
S=ROOT/"subjects/matched_target_normalization_v3"
EXPECTED={
 "candidate":"9b400e6eb1a95bacbd9c0cdb93b155ced0f72558",
 "provenance":"72a5cd689f55df84de73693371264f02ef4e7226",
 "test":"24e602f37e608d5abe19479c113feaff07acedea",
 "runtime":"9bc7ef820b9a0107dd7672e79f33ab3b77bd9160",
 "protocols":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 "registry":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "evidence":"f99b00e6dca735ffa7a790a414155b4f69856cf0",
 "matched":"438e2775b64bee5ed6e792522ab35ebd0d6e1771",
}
FILES={k:S/(k+(".py" if k in {"test","runtime"} else ".json")) for k in EXPECTED}

def blob(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(k):
 return json.loads(FILES[k].read_text(encoding="utf-8"))

for k,p in FILES.items():
 assert blob(p)==EXPECTED[k],(k,blob(p),EXPECTED[k])

spec=importlib.util.spec_from_file_location("norm",FILES["runtime"])
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

candidate=load("candidate"); provenance=load("provenance")
protocols=load("protocols"); registry=load("registry")
evidence=load("evidence"); matched=load("matched")

assert candidate["authority"]["protocols"]["git_blob_sha"]==EXPECTED["protocols"]
assert candidate["authority"]["predicate_registry"]["git_blob_sha"]==EXPECTED["registry"]
assert candidate["authority"]["evidence_bindings"]["git_blob_sha"]==EXPECTED["evidence"]
assert candidate["authority"]["matched_scope_residual"]["git_blob_sha"]==EXPECTED["matched"]
assert provenance["authority"]["candidate"]["git_blob_sha"]==EXPECTED["candidate"]
assert provenance["authority"]["protocols"]["git_blob_sha"]==EXPECTED["protocols"]
assert provenance["authority"]["predicate_registry"]["git_blob_sha"]==EXPECTED["registry"]
assert provenance["authority"]["evidence_bindings"]["git_blob_sha"]==EXPECTED["evidence"]
assert provenance["authority"]["matched_scope_residual"]["git_blob_sha"]==EXPECTED["matched"]

live=sorted({t for edge in matched["implications"] for t in edge["then"]})
candidate_ids=sorted(x["predicate_id"] for x in candidate["targets"])
provenance_ids=sorted(x["predicate_id"] for x in provenance["targets"])
assert len(live)==8
assert candidate_ids==live==provenance_ids

proved={x["predicate_id"] for x in evidence["claims"] if x.get("state")=="PROVED"}
assert proved.isdisjoint(live)

out=mod.evaluate(protocols,registry,candidate,provenance)
assert out["status"]=="PASS__ALL_TARGET_ATOMS_AND_METRICS_BOUND_TO_EXACT_FROZEN_SOURCE_LITERALS",out
assert out["verified_target_count"]==8,out
assert out["verified_atom_count"]==37,out
assert out["verified_metric_requirement_count"]==7,out
assert out["semantic_implication_verified"] is False,out
assert all(x["source_literal_binding_pass"] for x in out["target_results"]),out
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["new_reality_units_consumed"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

bad=json.loads(json.dumps(provenance))
bad["targets"][0]["atom_sources"][0]["sources"][0]["literal"]="not a current frozen literal"
failed=mod.evaluate(protocols,registry,candidate,bad)
assert failed["status"]=="FAIL_CLOSED",failed
assert any("LITERAL_NOT_FOUND" in e for e in failed["errors"]),failed

print("MATCHED_TARGET_NORMALIZATION_V3_INDEPENDENT_VERIFIED")
