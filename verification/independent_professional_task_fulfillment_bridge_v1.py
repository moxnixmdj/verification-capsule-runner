from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_task_fulfillment_bridge_v1 as f


def write_json(path: Path, doc) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
    return f.git_blob_sha(path)


def copy_scope_compiler(root: Path) -> None:
    src = Path("canonical/runtime/universal_scope_closure_compiler_v1.py")
    dst = root / f.SCOPE_COMPILER_PATH
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def make_bundle(root: Path, *, two: bool = True):
    copy_scope_compiler(root)
    task_id = "professional-task-x"
    task_sha = "a" * 64
    artifact_sha = "b" * 64
    obligations = [
        {"obligation_id": "O1", "semantics": "State the grounded conclusion", "required": True},
    ]
    if two:
        obligations.append(
            {"obligation_id": "O2", "semantics": "Provide the requested recommendation", "required": True}
        )
    digest = f.obligation_universe_digest(obligations)
    scope_id = f.task_scope_id(
        task_id=task_id, task_sha256=task_sha, obligation_digest=digest
    )
    scope = {
        "id": "scope-cert",
        "target_scope_id": scope_id,
        "basis": "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "verified": True,
        "independent": True,
        "scope_relation": "EXACT",
        "complete_target_case_set": True,
        "universe_identity_bound": True,
        "case_universe_digest": digest,
        "obligation_universe_digest": digest,
        "producer_id": "scope-producer",
    }
    sp = root / "canonical/evidence/scope.json"
    sb = write_json(sp, scope)
    sv = {
        "schema": f.SCOPE_VERIFY_SCHEMA,
        "subject_git_blob_sha": sb,
        "task_id": task_id,
        "task_sha256": task_sha,
        "obligation_universe_digest": digest,
        "target_scope_id": scope_id,
        "scope_complete": True,
        "pass": True,
        "independent_verified": True,
        "scope_complete_verified": True,
        "independent_verifier_id": "scope-verifier",
    }
    svp = root / "canonical/verification/scope.json"
    svb = write_json(svp, sv)
    scope_binding = {
        "certificate": {"path": "canonical/evidence/scope.json", "git_blob_sha": sb},
        "verification": {"path": "canonical/verification/scope.json", "git_blob_sha": svb},
    }

    bindings = []
    for index, obligation in enumerate(obligations, 1):
        oid = obligation["obligation_id"]
        semantics_sha = sha256(obligation["semantics"].encode("utf-8")).hexdigest()
        evidence_sha = str(index) * 64
        receipt = {
            "schema": f.RECEIPT_SCHEMA,
            "task_id": task_id,
            "task_sha256": task_sha,
            "artifact_sha256": artifact_sha,
            "obligation_id": oid,
            "obligation_semantics_sha256": semantics_sha,
            "obligation_universe_digest": digest,
            "target_scope_id": scope_id,
            "verdict": "PASS",
            "semantic_satisfaction_proved": True,
            "producer_id": "producer-" + oid,
            "evidence_sha256": evidence_sha,
        }
        rp = root / ("canonical/evidence/" + oid + ".json")
        rb = write_json(rp, receipt)
        verify = {
            "schema": f.VERIFY_SCHEMA,
            "subject_git_blob_sha": rb,
            "task_id": task_id,
            "task_sha256": task_sha,
            "artifact_sha256": artifact_sha,
            "obligation_id": oid,
            "obligation_semantics_sha256": semantics_sha,
            "obligation_universe_digest": digest,
            "target_scope_id": scope_id,
            "evidence_sha256": evidence_sha,
            "pass": True,
            "independent_verified": True,
            "semantic_satisfaction_verified": True,
            "independent_verifier_id": "verifier-" + oid,
        }
        vp = root / ("canonical/verification/" + oid + ".json")
        vb = write_json(vp, verify)
        bindings.append(
            {
                "obligation_id": oid,
                "receipt": {"path": "canonical/evidence/" + oid + ".json", "git_blob_sha": rb},
                "verification": {
                    "path": "canonical/verification/" + oid + ".json",
                    "git_blob_sha": vb,
                },
            }
        )

    bundle = {
        "task": {
            "task_id": task_id,
            "task_sha256": task_sha,
            "obligations": obligations,
            "obligation_scope_binding": scope_binding,
        },
        "artifact_sha256": artifact_sha,
        "obligation_bindings": bindings,
    }
    return bundle


class IndependentProfessionalTaskFulfillmentV1(unittest.TestCase):
    def test_happy_path_is_bounded_and_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            out = f.verify(make_bundle(Path(td)), repo_root=td)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["positive_task_fulfillment_authorized"])
        self.assertTrue(out["scope_complete"])
        self.assertEqual(out["obligation_count"], 2)
        self.assertEqual(out["verified_obligation_count"], 2)
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["owner_evaluator_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["gdpval_credit_delta"], 0)

    def test_scope_requires_separate_bound_verification(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            b["task"]["obligation_scope_binding"].pop("verification")
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("BOUND_REF_REQUIRED", out["errors"][0])

    def test_scope_producer_cannot_verify_itself(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            ref = b["task"]["obligation_scope_binding"]["verification"]
            p = root / ref["path"]
            doc = json.loads(p.read_text())
            doc["independent_verifier_id"] = "scope-producer"
            ref["git_blob_sha"] = write_json(p, doc)
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("OBLIGATION_SCOPE_PRODUCER_VERIFIER_NOT_INDEPENDENT", out["errors"][0])

    def test_scope_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            ref = b["task"]["obligation_scope_binding"]["certificate"]
            p = root / ref["path"]
            doc = json.loads(p.read_text())
            doc["producer_id"] = "changed"
            write_json(p, doc)
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("BOUND_BLOB_DRIFT", out["errors"][0])

    def test_scope_compiler_dependency_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            p = root / f.SCOPE_COMPILER_PATH
            p.write_text(p.read_text() + "\n# drift\n")
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_COMPILER_BLOB_DRIFT", out["errors"][0])

    def test_missing_required_obligation_binding_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            b["obligation_bindings"].pop()
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("OBLIGATION_BINDINGS_MISSING", out["errors"][0])

    def test_undeclared_extra_binding_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root, two=False)
            b["obligation_bindings"].append({"obligation_id": "EXTRA"})
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("UNDECLARED_OBLIGATION_BINDINGS", out["errors"][0])

    def test_artifact_identity_is_load_bearing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            b["artifact_sha256"] = "c" * 64
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("artifact_sha256", out["errors"][0])

    def test_semantic_verification_false_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            ref = b["obligation_bindings"][0]["verification"]
            p = root / ref["path"]
            doc = json.loads(p.read_text())
            doc["semantic_satisfaction_verified"] = False
            ref["git_blob_sha"] = write_json(p, doc)
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("semantic_satisfaction_verified", out["errors"][0])

    def test_semantic_producer_cannot_verify_itself(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            ref = b["obligation_bindings"][0]["verification"]
            p = root / ref["path"]
            doc = json.loads(p.read_text())
            doc["independent_verifier_id"] = "producer-O1"
            ref["git_blob_sha"] = write_json(p, doc)
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("OBLIGATION_PRODUCER_VERIFIER_NOT_INDEPENDENT", out["errors"][0])

    def test_task_obligation_semantics_change_invalidates_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = make_bundle(root)
            b["task"]["obligations"][0]["semantics"] = "Different requirement"
            out = f.verify(b, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertTrue(
            "OBLIGATION_SCOPE_TARGET_MISMATCH" in out["errors"][0]
            or "OBLIGATION_SCOPE_DIGEST_MISMATCH" in out["errors"][0]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
