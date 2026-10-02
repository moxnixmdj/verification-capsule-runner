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
    "canonical/runtime/proof_atom_receipt_index_v2.py": "ceca82ddaa0fee10385ba6888fdc5a0b27ae1ff3",
    "canonical/tests/test_proof_atom_receipt_index_v2.py": "20f3f69986776beb22bba59edc06dac7c536fb6e",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "b83839a34795794798d9cf27ef8e52cb440b6a68",
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

# Independent adversarial candidate-pointer semantics.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/verification/r.json"
    p.parent.mkdir(parents=True)
    content = '{"claim":"FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"}\n'
    p.write_text(content, encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    assert out["status"].startswith("PASS"), out
    row = next(x for x in out["atoms"] if x["proposition"] == "FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS")
    assert row["associated_target_predicates"] == ["CODING_FRONTIERCODE_GE_54_4"], row
    assert row["candidate_match_count"] == 1, row
    match = row["candidate_matches"][0]
    assert match["candidate_only"] is True
    assert match["source_class"] == "VERIFICATION_RECEIPT"
    assert match["git_blob_sha"] == blob_sha(p)

# Substring must not become a proposition match.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/verification/r.json"
    p.parent.mkdir(parents=True)
    p.write_text('{"claim":"FRONTIERCODE_FROZEN_BAR"}\n', encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    row = next(x for x in out["atoms"] if x["proposition"] == "FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS")
    assert row["candidate_match_count"] == 0, row

# Restatement sources must be excluded even if they contain exact literals.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    p = root / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"
    p.parent.mkdir(parents=True)
    p.write_text('{"requires":["FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]}\n', encoding="utf-8")
    out = build_index(frontier, overlay, root=root)
    row = next(x for x in out["atoms"] if x["proposition"] == "FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS")
    assert row["candidate_match_count"] == 0, row

# Discovery output must remain zero-credit and non-authoritative.
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
}
assert required_rules.issubset(set(gov["hard_rules"])), gov["hard_rules"]
assert gov["source_basis"]["expected_canonical_atoms"] == 40
assert gov["source_basis"]["atom_identity_namespace"] == "PA1"

# Re-run the exact Brain-authored adversarial test module inside the pinned capsule.
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
    "restatement_exclusion_verified": True,
    "semantic_substring_rejected": True,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
    "execution_authority": False,
    "promotion_authority": False,
}, indent=2, sort_keys=True))
