from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "runtime.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
    "brain_tests.py": "0684ec41a44484361c95c346c9e0692f5eede813",
    "governance.json": "f5cdd89ccc6f5b8e07066120c6431d6f660ca301",
    "overlay.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
    "frontier.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    "matched_subfrontier.json": "89162df13fae66edabaa53ac9c8d95a88829e3ec",
    "multitarget_activation.json": "39bbf3b99de2b7c992bdda411d9eb4625cbfb8b7",
    "matched_receipt.json": "14496949201835b086b41b10929e3a487468b028",
    "multitarget_receipt.json": "9bc287a29b4cab10dbfbd9250a4f4b26c2b7d07d",
}

def git_blob_sha(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name: str):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

for name,sha in EXPECTED.items():
    got=git_blob_sha(ROOT/name)
    assert got==sha,(name,got,sha)

spec=importlib.util.spec_from_file_location("basis_v2",ROOT/"runtime.py")
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

frontier=load("frontier.json")
overlay=load("overlay.json")
gov=load("governance.json")
matched_receipt=load("matched_receipt.json")
multi_receipt=load("multitarget_receipt.json")

# Receipt/source integrity for all refinement modes.
assert matched_receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert multi_receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
refs={x["parent_certificate_id"]:x for x in overlay["refinements"]}
matched=refs["MATCHED_SCOPE_BINDING_CERTIFICATE"]
assert matched["mode"]=="INDEPENDENTLY_VERIFIED_SEMANTIC_REPLACEMENT"
assert matched["source_blob_sha"]==EXPECTED["matched_subfrontier.json"]
assert matched["verification_receipt"].endswith("MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
for pid in ["CODING_PRIVATE_BAR_STRONGER_PROOF_CERTIFICATE","AA_BRIEFCASE_STRONGER_PROOF_CERTIFICATE"]:
    ref=refs[pid]
    assert ref["mode"]=="EXACT_REQUIREMENT_PARTITION"
    assert ref["source_blob_sha"]==EXPECTED["multitarget_activation.json"]
    assert ref["verification_receipt"].endswith("GLOBAL_ABDUCTIVE_AND_MULTITARGET_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

out=mod.compile_basis(frontier,overlay)
assert out["status"].startswith("PASS"),out
assert out["global_unresolved_predicate_count"]==31
assert out["global_certificate_count"]==17
assert out["refined_parent_count"]==3
assert out["leaf_requirement_occurrence_count"]==40
assert out["leaf_atom_count"]==40
assert out["exact_duplicate_savings"]==0
assert out["max_structural_target_fanout"]==3
assert all(x["atom_id"].startswith("PA1:") for x in out["atoms"]), "PA1 identity continuity broken"
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

by={x["proposition"]:x for x in out["atoms"]}
expected_targets={
 "FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS":["CODING_FRONTIERCODE_GE_54_4"],
 "CURSORBENCH_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS":["CODING_CURSORBENCH_GE_57_8"],
 "PROWORK_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS":["PROWORK_AA_BRIEFCASE_GE_1822"],
 "ARTIFACT_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS":["ARTIFACT_AA_BRIEFCASE_GE_1822"],
}
for prop,targets in expected_targets.items():
    assert by[prop]["associated_target_predicates"]==targets,(prop,by[prop])

# Regression: the two defects repaired after PR #1000 must fail if reintroduced.
bad=json.loads(json.dumps(overlay))
bad["refinements"][0].pop("source_blob_sha")
failed=mod.compile_basis(frontier,bad)
assert failed["status"]=="FAIL_CLOSED",failed
assert "REFINEMENT_SOURCE_BLOB_SHA_REQUIRED:MATCHED_SCOPE_BINDING_CERTIFICATE" in failed["errors"]

assert mod.atom_id("stable-proposition").startswith("PA1:")
assert "PRESERVE_PA1_CONTENT_ADDRESS_FOR_UNCHANGED_PROPOSITION_LITERALS" in gov["hard_rules"]
assert "SEMANTIC_REPLACEMENT_REQUIRES_PINNED_SOURCE_BLOB_SHA" in gov["hard_rules"]
assert gov["runtime_git_blob_sha"]==EXPECTED["runtime.py"]
assert gov["tests_git_blob_sha"]==EXPECTED["brain_tests.py"]
assert gov["inputs"]["refinement_overlay"]["git_blob_sha"]==EXPECTED["overlay.json"]

print(json.dumps({
  "status":"PASS",
  "exact_brain_blob_count":len(EXPECTED),
  "projection":{"unresolved":31,"refined_parents":3,"atoms":40,"max_fanout":3},
  "pa1_identity_continuity":True,
  "semantic_source_blob_pinning":True,
  "target_specific_associations_verified":4,
  "credit_delta":0
},indent=2,sort_keys=True))
