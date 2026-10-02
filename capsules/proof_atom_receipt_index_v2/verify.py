from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

EXPECTED = {
    "canonical/runtime/proof_atom_receipt_index_v2.py": "710071856e15f1561deb17347e7cf9cb0c477322",
    "canonical/tests/test_proof_atom_receipt_index_v2.py": "80f7a5ca4d4a7c35b0997f3e552c0ee23d3a0bfa",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "27fa9deb9ef591adb9e33b24bd8e971a74ef5e89",
    "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
}

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

for rel, expected in EXPECTED.items():
    got = blob_sha(ROOT / rel)
    assert got == expected, (rel, got, expected)

from canonical.runtime.proof_atom_receipt_index_v2 import build_index
from canonical.runtime.canonical_proof_atom_basis_v2 import compile_basis

frontier = json.loads((ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
overlay = json.loads((ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
gov = json.loads((ROOT / "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json").read_text())

basis = compile_basis(frontier, overlay)
assert basis["status"].startswith("PASS"), basis
assert basis["leaf_atom_count"] == 40, basis
assert all(row["atom_id"].startswith("PA1:") for row in basis["atoms"])
assert basis["capability_credit_delta"] == 0
assert basis["family_credit_delta"] == 0
assert basis["execution_authority"] is False
assert basis["promotion_authority"] is False

TARGET = "FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"

# Exact candidate pointer, target-specific association, and content address.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/verification/r.json"
    p.parent.mkdir(parents=True)
    content = json.dumps({"claim": TARGET}, separators=(",", ":")) + "\n"
    p.write_text(content, encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    assert out["status"].startswith("PASS"), out
    row = next(x for x in out["atoms"] if x["proposition"] == TARGET)
    assert row["associated_target_predicates"] == ["CODING_FRONTIERCODE_GE_54_4"], row
    assert row["candidate_match_count"] == 1, row
    assert row["stored_candidate_match_count"] == 1, row
    assert row["candidate_match_truncated"] is False, row
    match = row["candidate_matches"][0]
    assert match["candidate_only"] is True
    assert match["source_class"] == "VERIFICATION_RECEIPT"
    assert match["git_blob_sha"] == blob_sha(p)
    first_corpus_manifest = out["scanned_corpus_manifest_sha256"]
    first_atom_manifest = out["canonical_atom_manifest_sha256"]
    out2 = build_index(frontier, overlay, root=root)
    assert out2["scanned_corpus_manifest_sha256"] == first_corpus_manifest
    assert out2["canonical_atom_manifest_sha256"] == first_atom_manifest
    p.write_text(json.dumps({"claim": TARGET, "extra": 1}, separators=(",", ":")) + "\n", encoding="utf-8")
    out3 = build_index(frontier, overlay, root=root)
    assert out3["scanned_corpus_manifest_sha256"] != first_corpus_manifest
    assert out3["canonical_atom_manifest_sha256"] == first_atom_manifest

# Identifier-superstring false positive must be rejected.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/verification/r.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"claim": TARGET + "_EXTENDED"}) + "\n", encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    row = next(x for x in out["atoms"] if x["proposition"] == TARGET)
    assert row["candidate_match_count"] == 0, row

# Self-verification cannot become evidence for itself.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/verification/PROOF_ATOM_RECEIPT_INDEX_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"repeated_atom": TARGET}) + "\n", encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    row = next(x for x in out["atoms"] if x["proposition"] == TARGET)
    assert row["candidate_match_count"] == 0, row

# Declared-corpus lexical projections cannot bootstrap evidence.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/governance/DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_V1_PART_0.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"lexical_projection": TARGET}) + "\n", encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    row = next(x for x in out["atoms"] if x["proposition"] == TARGET)
    assert row["candidate_match_count"] == 0, row

# Storage cap must never hide the true match count.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    d = root / "canonical/verification"
    d.mkdir(parents=True)
    for i in range(65):
        (d / f"r{i:02d}.json").write_text(json.dumps({"claim": TARGET}) + "\n", encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    row = next(x for x in out["atoms"] if x["proposition"] == TARGET)
    assert row["candidate_match_count"] == 65, row
    assert row["stored_candidate_match_count"] == 64, row
    assert row["candidate_match_truncated"] is True, row
    assert out["atoms_with_truncated_candidate_lists"] == 1, out

# Discovery output remains zero-credit and non-authoritative.
with tempfile.TemporaryDirectory() as td:
    out = build_index(frontier, overlay, root=Path(td))
    assert out["canonical_atom_count"] == 40
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False

required_rules = {
    "EXACT_LITERAL_OCCURRENCE_IS_ONLY_A_CANDIDATE_POINTER",
    "EVERY_MATCH_CONTENT_ADDRESSED_BY_GIT_BLOB_SHA",
    "PRESERVE_PA1_ATOM_IDS",
    "NO_SEMANTIC_EQUIVALENCE_FROM_NAMES_OR_PROSE",
    "ZERO_FRESH_REALITY",
    "RECEIPT_INDEX_SELF_VERIFICATION_ARTIFACTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE",
    "DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_RESTATEMENTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE",
}
assert required_rules.issubset(set(gov["hard_rules"])), gov["hard_rules"]
assert gov["source_basis"]["expected_canonical_atoms"] == 40
assert gov["source_basis"]["atom_identity_namespace"] == "PA1"
assert gov["runtime_git_blob_sha"] == EXPECTED["canonical/runtime/proof_atom_receipt_index_v2.py"]
assert gov["tests_git_blob_sha"] == EXPECTED["canonical/tests/test_proof_atom_receipt_index_v2.py"]

# Re-run exact Brain-authored hardened adversarial tests inside the pinned capsule.
cp = subprocess.run(
    [sys.executable, "-m", "unittest", "canonical.tests.test_proof_atom_receipt_index_v2", "-v"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
print(cp.stdout)
print(cp.stderr, file=sys.stderr)
assert cp.returncode == 0, cp.returncode

print(json.dumps({
    "status": "PASS",
    "exact_brain_blob_count": len(EXPECTED),
    "canonical_atom_count": 40,
    "pa1_identity_preserved": True,
    "target_specific_association_verified": True,
    "candidate_pointer_only": True,
    "token_boundary_verified": True,
    "corpus_manifest_verified": True,
    "atom_manifest_verified": True,
    "match_truncation_honesty_verified": True,
    "self_reflection_quarantine_verified": True,
    "declared_corpus_restatement_quarantine_verified": True,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
    "execution_authority": False,
    "promotion_authority": False,
}, indent=2, sort_keys=True))
