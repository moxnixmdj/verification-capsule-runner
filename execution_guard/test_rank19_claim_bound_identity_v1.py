from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id
from execution_guard.rank19_claim_bound_identity_v1 import resolve_claim_bound_identity

SLOT = "terminal-bench-science/diag-chipseq::trial-0"
DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
CLAIM = "sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class Rank19ClaimBoundIdentityTests(unittest.TestCase):
    def test_exact_brain_v2_identity(self):
        self.assertEqual(
            logical_attempt_id(
                slot_id=SLOT,
                task_digest=DIGEST,
                execution_claim_binding_digest=CLAIM,
            ),
            ATTEMPT,
        )

    def test_resolver_reads_content_addressed_public_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "capsules").mkdir()
            (root / "execution_guard").mkdir()

            authority_rel = "capsules/RANK19_PUBLIC_AUTHORITY_BINDING_V2.json"
            authority_path = root / authority_rel
            authority = {
                "slot_id": SLOT,
                "task_digest": DIGEST,
                "logical_attempt_id": ATTEMPT,
                "logical_attempt_identity_basis": (
                    "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST"
                ),
                "execution_claim_binding_digest": CLAIM,
                "claim_epoch_id": "RANK19_V14_CLAIM_BOUND_IDENTITY_20261010_V1",
            }
            authority_path.write_text(json.dumps(authority, sort_keys=True) + "\n", encoding="utf-8")

            surface = {
                "slot_id": SLOT,
                "task_digest": DIGEST,
                "authority": {
                    "path": authority_rel,
                    "git_blob_sha": git_blob(authority_path),
                },
            }
            (root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json").write_text(
                json.dumps(surface, sort_keys=True) + "\n", encoding="utf-8"
            )

            out = resolve_claim_bound_identity(
                root=root,
                surface_rel="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json",
                expected_slot_id=SLOT,
                expected_task_digest=DIGEST,
            )
            self.assertEqual(out["logical_attempt_id"], ATTEMPT)
            self.assertEqual(out["execution_claim_binding_digest"], CLAIM)

    def test_authority_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "capsules").mkdir()
            (root / "execution_guard").mkdir()
            authority_rel = "capsules/a.json"
            authority_path = root / authority_rel
            authority_path.write_text(
                json.dumps(
                    {
                        "slot_id": SLOT,
                        "task_digest": DIGEST,
                        "logical_attempt_id": ATTEMPT,
                        "logical_attempt_identity_basis": (
                            "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST"
                        ),
                        "execution_claim_binding_digest": CLAIM,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            expected = git_blob(authority_path)
            authority_path.write_text(authority_path.read_text() + " ", encoding="utf-8")
            (root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json").write_text(
                json.dumps(
                    {
                        "slot_id": SLOT,
                        "task_digest": DIGEST,
                        "authority": {"path": authority_rel, "git_blob_sha": expected},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "AUTHORITY_BLOB_MISMATCH"):
                resolve_claim_bound_identity(
                    root=root,
                    surface_rel="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json",
                    expected_slot_id=SLOT,
                    expected_task_digest=DIGEST,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
