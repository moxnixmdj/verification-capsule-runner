from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
manifest = json.loads((ROOT / "EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for rel, expected in manifest["exact_brain_blobs"].items():
    actual = git_blob_sha(ROOT / rel)
    assert actual == expected, (rel, actual, expected)

sys.path.insert(0, str(ROOT))
subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        str(ROOT / "canonical/runtime/canonical_proof_atom_basis_v2.py"),
        str(ROOT / "canonical/runtime/proof_atom_receipt_index_v2.py"),
        str(ROOT / "canonical/runtime/proof_atom_candidate_universe_coverage_v1.py"),
    ],
    check=True,
)
subprocess.run(
    [
        sys.executable,
        "-m",
        "unittest",
        "canonical.tests.test_proof_atom_candidate_universe_coverage_v1",
        "-v",
    ],
    cwd=ROOT,
    check=True,
)

from canonical.runtime.proof_atom_candidate_universe_coverage_v1 import (
    MAX_FILE_BYTES,
    audit_coverage,
)


def roots(root: pathlib.Path) -> None:
    for rel in (
        "canonical/verification",
        "canonical/capabilities",
        "canonical/governance",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    roots(root)
    (root / "canonical/verification/r.json").write_text('{"claim":"R1"}\n', encoding="utf-8")
    clean = audit_coverage(root=root)
    assert clean["status"].startswith("PASS"), clean
    assert clean["candidate_selection_parity"] is True
    assert clean["negative_literal_exhaustive_within_configured_candidate_set"] is True
    assert clean["negative_literal_exhaustive_over_supported_text_in_search_roots"] is True
    assert clean["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"] is True

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    roots(root)
    (root / "canonical/verification/large.json").write_bytes(b"x" * (MAX_FILE_BYTES + 1))
    oversized = audit_coverage(root=root)
    assert oversized["status"].startswith("PASS"), oversized
    assert oversized["oversized_supported_text_count"] == 1
    assert oversized["negative_literal_exhaustive_within_configured_candidate_set"] is True
    assert oversized["negative_literal_exhaustive_over_supported_text_in_search_roots"] is False
    assert oversized["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"] is False

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    roots(root)
    (root / "canonical/verification/r.json").write_text('{"claim":"R1"}\n', encoding="utf-8")
    (root / "canonical/verification/raw.bin").write_bytes(b"R1")
    unsupported = audit_coverage(root=root)
    assert unsupported["status"].startswith("PASS"), unsupported
    assert unsupported["unsupported_suffix_count"] == 1
    assert unsupported["negative_literal_exhaustive_over_supported_text_in_search_roots"] is True
    assert unsupported["negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots"] is False

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    roots(root)
    (root / "canonical/verification/r.json").write_bytes(b"\xff\xfe\x00")
    malformed = audit_coverage(root=root)
    assert malformed["status"] == "FAIL_CLOSED", malformed
    assert malformed["scan_gap_count"] == 1
    assert malformed["negative_literal_exhaustive_within_configured_candidate_set"] is False

for out in (clean, oversized, unsupported, malformed):
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False

print(
    json.dumps(
        {
            "status": "PASS",
            "brain_ref": manifest["brain_ref"],
            "exact_brain_blob_count": len(manifest["exact_brain_blobs"]),
            "unit_tests": "PASS",
            "candidate_selection_parity_clean_fixture": clean["candidate_selection_parity"],
            "configured_candidate_negative_scope_explicit": True,
            "supported_text_negative_scope_explicit": True,
            "full_search_root_negative_scope_explicit": True,
            "oversize_supported_text_blocks_scope_widening": True,
            "unsupported_suffix_blocks_scope_widening": True,
            "non_utf8_supported_text_fails_closed": True,
            "credit_delta": 0,
        },
        indent=2,
        sort_keys=True,
    )
)
