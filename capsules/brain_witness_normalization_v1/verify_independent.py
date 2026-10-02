from __future__ import annotations
import copy, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from canonical.runtime.brain_witness_normalization_verifier_v1 import evaluate

EXPECTED = {
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "f500b56e7349ce8c0f97cfd0bd1db4888ec6887c",
  "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json": "68af5a081b87ce83db6f69e864843d090206db4c",
  "canonical/runtime/brain_witness_normalization_verifier_v1.py": "b6b54af71d62624a0682dee9c86611752bcb2e81",
  "canonical/tests/test_brain_witness_normalization_v1.py": "5c1673ac68a25b011981e889431f83b175911869"
}

def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, expected in EXPECTED.items():
    actual = git_blob_sha(ROOT / rel)
    assert actual == expected, (rel, actual, expected)

source = json.loads((ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json").read_text())
normalized = json.loads((ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json").read_text())
source_sha = git_blob_sha(ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")

out = evaluate(source, normalized, source_sha)
assert out["pass"] is True, out
assert out["witness_count"] == 9, out
assert out["semantic_implication_verified"] is False, out
assert out["acceptance_credit_delta"] == 0, out
assert out["family_credit_delta"] == 0, out

# Any invented target atom must fail closed.
m = copy.deepcopy(normalized)
m["witnesses"][0]["normalized_target_atoms"] = ["dimension:invented"]
bad = evaluate(source, m, source_sha)
assert bad["pass"] is False, bad

# Any invented semantic implication must fail closed.
m = copy.deepcopy(normalized)
m["witnesses"][0]["semantic_implications"] = [{"to":"invented"}]
bad = evaluate(source, m, source_sha)
assert bad["pass"] is False, bad

# Removing a proved witness must fail exact recomputation.
m = copy.deepcopy(normalized)
m["witnesses"] = m["witnesses"][:-1]
m["witness_count"] -= 1
bad = evaluate(source, m, source_sha)
assert bad["pass"] is False, bad

# Adding a non-PROVED source claim must not become a witness.
nonproved = [x for x in source["claims"] if x.get("state") != "PROVED"]
assert nonproved, "expected at least one unresolved/blocker claim"
assert all(x.get("predicate_id") not in {w["source_predicate_id"] for w in normalized["witnesses"]} for x in nonproved)

print("independent Brain witness normalization verification: PASS")
