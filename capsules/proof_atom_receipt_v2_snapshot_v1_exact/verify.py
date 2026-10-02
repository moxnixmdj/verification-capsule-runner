from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_REPO = "moxnixmdj/brain"
SOURCE_HEAD = "a79e213df4522389373e24bd873ebebada5300bc"

EXPECTED = {
    "canonical/runtime/proof_atom_receipt_index_v2.py": "7faf9f16acc2b18c501f0d08164833027d3d68fa",
    "canonical/tests/test_proof_atom_receipt_index_v2.py": "14103ef7c96330a281367409a5b76a0a74e7129d",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "b9803927a2e1f2935686f1d37382e4d2d8d968ed",
    "canonical/runtime/proof_atom_receipt_snapshot_v1.py": "759ae4a3be0d8a8015225568372b1582c5cbb660",
    "canonical/tests/test_proof_atom_receipt_snapshot_v1.py": "c557cf03d4d5a79c098db3e743786323dce706f9",
    "canonical/governance/PROOF_ATOM_RECEIPT_SNAPSHOT_V1.json": "4799de99fe84941622e39b8f2c22f654300e7dd4",
    "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for rel, expected in EXPECTED.items():
    got = git_blob_sha(ROOT / rel)
    assert got == expected, (rel, got, expected)

sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

cp = subprocess.run(
    [
        sys.executable,
        "-m",
        "unittest",
        "canonical.tests.test_proof_atom_receipt_index_v2",
        "canonical.tests.test_proof_atom_receipt_snapshot_v1",
        "-v",
    ],
    text=True,
    capture_output=True,
)
if cp.returncode != 0:
    print(cp.stdout)
    print(cp.stderr, file=sys.stderr)
    raise SystemExit(cp.returncode)

index_mod = importlib.import_module("canonical.runtime.proof_atom_receipt_index_v2")
frontier = json.loads(
    (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(
        encoding="utf-8"
    )
)
overlay = json.loads(
    (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(
        encoding="utf-8"
    )
)

# Compile the exact active basis while scanning an intentionally empty evidence universe.
# This proves the pinned indexer consumes the active V2 basis exactly, without pretending
# candidate discovery itself is semantic evidence.
import tempfile
with tempfile.TemporaryDirectory() as td:
    live = index_mod.build_index(frontier, overlay, root=Path(td))

assert live["status"].startswith("PASS"), live
assert live["canonical_atom_count"] == 40, live
assert live["candidate_match_count"] == 0, live
assert live["atoms_with_candidate_matches"] == 0, live
assert live["atoms_without_candidate_matches"] == 40, live
assert all(row["atom_id"].startswith("PA1:") for row in live["atoms"]), live
assert live["capability_credit_delta"] == 0
assert live["family_credit_delta"] == 0
assert live["execution_authority"] is False
assert live["promotion_authority"] is False
assert len(live["canonical_atom_manifest_sha256"]) == 64
assert len(live["scanned_corpus_manifest_sha256"]) == 64

index_gov = json.loads(
    (ROOT / "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json").read_text(
        encoding="utf-8"
    )
)
snapshot_gov = json.loads(
    (ROOT / "canonical/governance/PROOF_ATOM_RECEIPT_SNAPSHOT_V1.json").read_text(
        encoding="utf-8"
    )
)
assert index_gov["capability_credit_delta"] == 0
assert index_gov["family_credit_delta"] == 0
assert index_gov["execution_authority"] is False
assert index_gov["promotion_authority"] is False
assert snapshot_gov["capability_credit_delta"] == 0
assert snapshot_gov["family_credit_delta"] == 0
assert snapshot_gov["execution_authority"] is False
assert snapshot_gov["promotion_authority"] is False

print(
    json.dumps(
        {
            "status": "PASS",
            "source_repo": SOURCE_REPO,
            "source_head": SOURCE_HEAD,
            "exact_brain_blob_count": len(EXPECTED),
            "index_and_snapshot_unit_suites": "PASS",
            "canonical_atom_count": live["canonical_atom_count"],
            "atom_namespace": "PA1",
            "candidate_semantic_credit": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        },
        indent=2,
        sort_keys=True,
    )
)
