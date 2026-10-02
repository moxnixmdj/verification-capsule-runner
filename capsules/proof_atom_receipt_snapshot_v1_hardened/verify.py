from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def blob_sha(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for src,expected in m["exact_brain_blobs"].items():
    got=blob_sha(ROOT/src)
    assert got==expected,(src,got,expected)

sys.path.insert(0,str(ROOT))
subprocess.run([sys.executable,"-m","py_compile",
    str(ROOT/"canonical/runtime/canonical_proof_atom_basis_v2.py"),
    str(ROOT/"canonical/runtime/proof_atom_receipt_index_v2.py"),
    str(ROOT/"canonical/runtime/proof_atom_receipt_snapshot_v1.py")],check=True)
subprocess.run([sys.executable,"-m","unittest",
    "canonical.tests.test_proof_atom_receipt_index_v2",
    "canonical.tests.test_proof_atom_receipt_snapshot_v1","-v"],cwd=ROOT,check=True)

from canonical.runtime.proof_atom_receipt_index_v2 import build_index
frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
with tempfile.TemporaryDirectory() as td:
    out=build_index(frontier,overlay,root=pathlib.Path(td))
assert out["status"].startswith("PASS"),out
assert out["canonical_atom_count"]==40,out
assert out["candidate_match_count"]==0,out
assert all(x["atom_id"].startswith("PA1:") for x in out["atoms"])
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
assert out["execution_authority"] is False and out["promotion_authority"] is False

gov=json.loads((ROOT/"canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json").read_text())
assert gov["runtime_git_blob_sha"]==m["exact_brain_blobs"]["canonical/runtime/proof_atom_receipt_index_v2.py"]
assert gov["tests_git_blob_sha"]==m["exact_brain_blobs"]["canonical/tests/test_proof_atom_receipt_index_v2.py"]
assert "RECEIPT_INDEX_SELF_VERIFICATION_ARTIFACTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE" in gov["hard_rules"]
assert "DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_RESTATEMENTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE" in gov["hard_rules"]

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(m["exact_brain_blobs"]),
 "canonical_atom_count":40,
 "pa1_identity_preserved":True,
 "self_reflection_quarantine_verified":True,
 "sealed_snapshot_tests_verified":True,
 "credit_delta":0
},indent=2,sort_keys=True))
