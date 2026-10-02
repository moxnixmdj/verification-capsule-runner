import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def blob(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

for rel, expected in m["exact_brain_blobs"].items():
    actual=blob(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

gov=json.loads((ROOT/"canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json").read_text())
for rule in m["required_quarantines"]:
    assert rule in gov["hard_rules"],rule
assert gov["runtime_git_blob_sha"]==m["exact_brain_blobs"]["canonical/runtime/proof_atom_receipt_index_v2.py"]
assert gov["tests_git_blob_sha"]==m["exact_brain_blobs"]["canonical/tests/test_proof_atom_receipt_index_v2.py"]
assert gov["capability_credit_delta"]==0 and gov["family_credit_delta"]==0
assert gov["execution_authority"] is False and gov["promotion_authority"] is False
print("exact current Brain V2 self-reflection verification inputs: PASS")
