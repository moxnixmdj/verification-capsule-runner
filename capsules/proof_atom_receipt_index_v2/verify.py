from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
m = json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def git_blob_sha(path: pathlib.Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for src, expected in m["exact_brain_blobs"].items():
    actual=git_blob_sha(ROOT/src)
    assert actual==expected,(src,actual,expected)

sys.path.insert(0,str(ROOT))
subprocess.run([sys.executable,"-m","py_compile",
    str(ROOT/"canonical/runtime/canonical_proof_atom_basis_v2.py"),
    str(ROOT/"canonical/runtime/proof_atom_receipt_index_v2.py")],check=True)
subprocess.run([sys.executable,"-m","unittest",
    "canonical.tests.test_proof_atom_receipt_index_v2","-v"],cwd=ROOT,check=True)

from canonical.runtime.proof_atom_receipt_index_v2 import build_index
frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
with tempfile.TemporaryDirectory() as td:
    out=build_index(frontier,overlay,root=pathlib.Path(td))
assert out["status"].startswith("PASS"),out
assert out["canonical_atom_count"]==40,out
assert out["candidate_match_count"]==0,out
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert all(x["atom_id"].startswith("PA1:") for x in out["atoms"])
by={x["proposition"]:x for x in out["atoms"]}
assert by["FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["CODING_FRONTIERCODE_GE_54_4"]
assert by["ARTIFACT_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["ARTIFACT_AA_BRIEFCASE_GE_1822"]
print(json.dumps({
  "status":"PASS",
  "exact_brain_blob_count":len(m["exact_brain_blobs"]),
  "canonical_atom_count":out["canonical_atom_count"],
  "pa1_identity_preserved":True,
  "target_specific_refinement_associations":True,
  "credit_delta":0
},indent=2,sort_keys=True))
