from __future__ import annotations
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRAIN = ROOT / "brain"
sys.path.insert(0, str(BRAIN))

EXPECTED = {
    "canonical/runtime/existing_receipt_semantic_candidate_miner_v2.py": "4646bf8e7cce1192612fe734383e8cb2c6afb1a1",
    "canonical/tests/test_existing_receipt_semantic_candidate_miner_v2.py": "98ebfaba62a2a0ec0b66044c02bd7b50d4e7601b",
    "canonical/governance/EXISTING_RECEIPT_SEMANTIC_CANDIDATE_MINER_V2.json": "dcdd8ba1e4cd6ac2772845ee2df5e58a28b54df6",
}

def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, expected in EXPECTED.items():
    got = blob_sha(BRAIN / rel)
    assert got == expected, (rel, got, expected)

from canonical.runtime import existing_receipt_semantic_candidate_miner_v2 as miner

suite = unittest.defaultTestLoader.loadTestsFromName(
    "canonical.tests.test_existing_receipt_semantic_candidate_miner_v2"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), "semantic candidate miner v2 tests failed"

gov = json.loads(
    (BRAIN / "canonical/governance/EXISTING_RECEIPT_SEMANTIC_CANDIDATE_MINER_V2.json").read_text()
)
assert gov["runtime"]["git_blob_sha"] == EXPECTED["canonical/runtime/existing_receipt_semantic_candidate_miner_v2.py"]
assert gov["tests"]["git_blob_sha"] == EXPECTED["canonical/tests/test_existing_receipt_semantic_candidate_miner_v2.py"]
assert tuple(gov["global_reuse_search_roots"]) == miner.SEARCH_ROOTS
assert "RUNTIME_TEST_WORKFLOW_AND_PRIOR_DISCOVERY_OUTPUTS_CANNOT_BECOME_GLOBAL_REUSE_EVIDENCE" in gov["hard_rules"]
assert "ACTUAL_MATCH_COUNT_MUST_REMAIN_SEPARATE_FROM_STORED_CAPPED_CANDIDATES" in gov["hard_rules"]
assert miner.excluded_from_global_reuse(Path("EXISTING_RECEIPT_SEMANTIC_CANDIDATE_MINING_20261002_V1.json"))
assert result.testsRun >= 5

print(json.dumps({
    "status": "PASS",
    "exact_brain_blob_count": len(EXPECTED),
    "tests_run": result.testsRun,
    "verified": [
        "EXACT_RUNTIME_TEST_GOVERNANCE_BLOB_BINDING",
        "SELF_REFLECTION_EXCLUSION",
        "IDENTIFIER_SUPERSTRING_REJECTION",
        "CONTENT_ADDRESSED_CANDIDATES",
        "CONTENT_SENSITIVE_CORPUS_MANIFEST",
        "EXPLICIT_MATCH_TRUNCATION",
        "WITNESS_PATH_ROOT_CONTAINMENT",
        "ZERO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_PROMOTION_CREDIT"
    ],
    "new_reality_units_consumed": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0
}, indent=2, sort_keys=True))
