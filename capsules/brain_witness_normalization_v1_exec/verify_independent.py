from __future__ import annotations
import hashlib, json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from canonical.runtime.brain_witness_normalization_verifier_v1 import evaluate

EXPECTED_BRAIN_BLOBS = {
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "f500b56e7349ce8c0f97cfd0bd1db4888ec6887c",
    "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json": "68af5a081b87ce83db6f69e864843d090206db4c",
    "canonical/runtime/brain_witness_normalization_verifier_v1.py": "b6b54af71d62624a0682dee9c86611752bcb2e81",
    "canonical/tests/test_brain_witness_normalization_v1.py": "5c1673ac68a25b011981e889431f83b175911869"
}

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for rel, expected in EXPECTED_BRAIN_BLOBS.items():
    actual = blob_sha(ROOT / rel)
    assert actual == expected, (rel, actual, expected)

source_path = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
norm_path = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"
source = json.loads(source_path.read_text())
norm = json.loads(norm_path.read_text())

out = evaluate(source, norm, blob_sha(source_path))
assert out["pass"] is True, out
assert out["status"] == "PASS__EXACT_CONTENT_ADDRESSED_WITNESS_NORMALIZATION__ZERO_SEMANTIC_CREDIT", out
assert out["witness_count"] == 9, out
assert out["semantic_implication_verified"] is False, out
assert out["acceptance_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["new_reality_units_consumed"] == 0

bad = json.loads(json.dumps(norm))
bad["witnesses"][0]["normalized_target_atoms"] = ["dimension:invented"]
b = evaluate(source, bad, blob_sha(source_path))
assert b["pass"] is False and "NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION" in b["errors"], b

bad2 = json.loads(json.dumps(norm))
bad2["authority"]["evidence_bindings"]["git_blob_sha"] = "bad"
b2 = evaluate(source, bad2, blob_sha(source_path))
assert b2["pass"] is False and "SOURCE_BLOB_AUTHORITY_MISMATCH" in b2["errors"], b2

bad3 = json.loads(json.dumps(norm))
bad3["witnesses"][0]["scope_complete"] = False
b3 = evaluate(source, bad3, blob_sha(source_path))
assert b3["pass"] is False, b3

print("independent Brain witness normalization verification: PASS")
