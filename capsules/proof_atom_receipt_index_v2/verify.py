from __future__ import annotations
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRAIN = ROOT / "brain"
sys.path.insert(0, str(BRAIN))

EXPECTED = {
    "canonical/runtime/proof_atom_receipt_index_v2.py": "ceca82ddaa0fee10385ba6888fdc5a0b27ae1ff3",
    "canonical/tests/test_proof_atom_receipt_index_v2.py": "20f3f69986776beb22bba59edc06dac7c536fb6e",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "b83839a34795794798d9cf27ef8e52cb440b6a68",
    "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
    "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
}

def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, expected in EXPECTED.items():
    got = blob_sha(BRAIN / rel)
    assert got == expected, (rel, got, expected)

from canonical.runtime import canonical_proof_atom_basis_v2 as basis
from canonical.runtime import proof_atom_receipt_index_v2 as idx

suite = unittest.defaultTestLoader.loadTestsFromName(
    "canonical.tests.test_proof_atom_receipt_index_v2"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), "Brain V2 receipt-index test suite failed"

frontier = json.loads((BRAIN / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
overlay = json.loads((BRAIN / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
compiled = basis.compile_basis(frontier, overlay)
assert compiled["status"].startswith("PASS"), compiled
assert compiled["leaf_atom_count"] == 40, compiled
assert len(compiled["atoms"]) == 40

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "canonical/verification").mkdir(parents=True)
    (root / "canonical/governance").mkdir(parents=True)
    prop = compiled["atoms"][0]["proposition"]
    payload = json.dumps({"independent_claim": prop}, sort_keys=True) + "\n"
    evidence = root / "canonical/verification/evidence.json"
    evidence.write_text(payload, encoding="utf-8")

    # Deliberate restatement in a forbidden scheduler/authority filename must be ignored.
    excluded = root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
    excluded.write_text(json.dumps({"restate": prop}) + "\n", encoding="utf-8")

    out = idx.build_index(frontier, overlay, root=root)
    assert out["status"].startswith("PASS"), out
    assert out["canonical_atom_count"] == 40
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False

    by_prop = {a["proposition"]: a for a in out["atoms"]}
    row = by_prop[prop]
    assert row["candidate_match_count"] == 1, row
    assert row["candidate_matches"][0]["path"] == "canonical/verification/evidence.json"
    assert row["candidate_matches"][0]["git_blob_sha"] == blob_sha(evidence)

    # Index identity must exactly equal the independently recomputed basis identity.
    expected_rows = {
        a["proposition"]: (a["atom_id"], a["associated_target_predicates"])
        for a in compiled["atoms"]
    }
    for r in out["atoms"]:
        atom_id, targets = expected_rows[r["proposition"]]
        assert r["atom_id"] == atom_id
        assert r["associated_target_predicates"] == targets

gov = json.loads((BRAIN / "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json").read_text())
assert gov["source_basis"]["expected_canonical_atoms"] == 40
assert gov["source_basis"]["atom_identity_namespace"] == "PA1"
assert "EXACT_LITERAL_OCCURRENCE_IS_ONLY_A_CANDIDATE_POINTER" in gov["hard_rules"]
assert "NO_SCOPE_RELATION_METRIC_BOUND_ACCEPTANCE_CAPABILITY_OR_FAMILY_CREDIT_FROM_INDEX" in gov["hard_rules"]

print(json.dumps({
    "status": "PASS",
    "exact_brain_blob_count": len(EXPECTED),
    "canonical_atom_count": 40,
    "brain_unit_tests_passed": result.testsRun,
    "independent_checks": [
        "EXACT_BLOB_HASH_BINDING",
        "LIVE_V2_BASIS_RECOMPUTATION",
        "PA1_IDENTITY_EQUALITY",
        "TARGET_ASSOCIATION_EQUALITY",
        "CONTENT_ADDRESS_MATCH",
        "AUTHORITY_RESTATEMENT_EXCLUSION",
        "ZERO_CREDIT_FAIL_CLOSED"
    ],
    "new_reality_units_consumed": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0
}, indent=2, sort_keys=True))
