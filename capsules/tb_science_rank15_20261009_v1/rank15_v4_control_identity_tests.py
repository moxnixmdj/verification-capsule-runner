#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import rank15_execution_identity_v1 as identity
import rank15_finalize_receipt_v4 as finalizer


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.surface_path = root / identity.SURFACE_REL
        self.activation_rel = "capsules/tb_science_rank15_20261009_v1/ACTIVATE_RANK15_V4_PR.json"
        self.workflow_rel = ".github/workflows/execute-tb-science-rank15-20261009-v4.yml"
        write(root / self.workflow_rel, "synthetic-v4-workflow\n")
        write(root / self.activation_rel, {"activate": True})

        self.paths = {}
        for label in (
            "authority","ledger","epoch","execution_claim","invariant_registry","admission_guard",
            "preflight","finalizer","planner","agent","prestart_guard","transport",
            "zero_exposure_tests","all_cycle_proof","start_cas","generic_start_cas",
            "generic_ref_store","execution_identity",
        ):
            rel = "fixture/" + label + ".txt"
            self.paths[label] = rel
            write(root / rel, label + "-v1\n")

        runtime = {
            k: {"path": self.paths[k], "git_blob_sha": git_blob(root / self.paths[k])}
            for k in (
                "planner","agent","prestart_guard","transport","zero_exposure_tests",
                "all_cycle_proof","start_cas","generic_start_cas","generic_ref_store",
                "finalizer","preflight","admission_guard","execution_identity",
            )
        }
        self.behavior_rel = "fixture/behavior.json"
        write(root / self.behavior_rel, {
            "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_BEHAVIOR_V4",
            "runtime_bindings":runtime,
        })
        control = {
            k: {"path": self.paths[k], "git_blob_sha": git_blob(root / self.paths[k])}
            for k in (
                "authority","ledger","epoch","execution_claim","invariant_registry",
                "admission_guard","preflight","finalizer",
            )
        }
        control["behavior"] = {
            "path": self.behavior_rel,
            "git_blob_sha": git_blob(root / self.behavior_rel),
        }
        self.surface = {
            "schema":"PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1",
            "slot_id":identity.SLOT_ID,
            "task_digest":identity.TASK_DIGEST,
            "workflow_path":self.workflow_rel,
            "workflow_git_blob_sha":git_blob(root / self.workflow_rel),
            "activation_path":self.activation_rel,
            **control,
        }
        write(self.surface_path, self.surface)
        self.guard = {"logical_attempt_id":"a"*64}
        write(root / "RANK15_PRESTART_GUARD.json", self.guard)

    def compiled(self):
        return identity.build_execution_identity(self.root)

    def cas(self):
        compiled = self.compiled()
        return {
            "pass":True,
            "acquired":True,
            "task_started":True,
            "slot_id":identity.SLOT_ID,
            "task_digest":identity.TASK_DIGEST,
            "generic_cas_key":finalizer._slot_start_key(),
            "logical_attempt_id":"a"*64,
            "runtime_identity_sha256":compiled["runtime_identity_sha256"],
            "control_identity_sha256":compiled["control_identity_sha256"],
            "prestart_receipt_sha256":identity.sha256_file(self.root/"RANK15_PRESTART_GUARD.json"),
            "durable_record_sha256":"b"*64,
            "workflow_git_blob_sha":compiled["workflow_git_blob_sha"],
            "authority_git_blob_sha":compiled["control_binding_blobs"]["authority"],
            "activation_git_blob_sha":identity.activation_blob(self.root, compiled["surface"]),
            "replay_authority":False,
            "replacement_carrier_authority":False,
        }

    def reseal(self, label: str, payload: str):
        rel = self.paths[label]
        write(self.root / rel, payload)
        self.surface[label]["git_blob_sha"] = git_blob(self.root / rel)
        write(self.surface_path, self.surface)


class Tests(unittest.TestCase):
    def test_exact_bound_receipt_passes(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(Path(td))
            errors,_=identity.validate_bound_start(f.root,guard=f.guard,cas=f.cas())
            self.assertEqual(errors,[])

    def test_epoch_reseal_invalidates_old_start(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(Path(td)); old=f.cas()
            f.reseal("epoch","epoch-v2\n")
            errors,_=identity.validate_bound_start(f.root,guard=f.guard,cas=old)
            self.assertIn("BOUND_START_IDENTITY_INVALID:CONTROL_IDENTITY_MATCH",errors)
            self.assertIn("BOUND_START_IDENTITY_INVALID:RUNTIME_IDENTITY_MATCH",errors)

    def test_claim_reseal_invalidates_old_start(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(Path(td)); old=f.cas()
            f.reseal("execution_claim","claim-v2\n")
            errors,_=identity.validate_bound_start(f.root,guard=f.guard,cas=old)
            self.assertIn("BOUND_START_IDENTITY_INVALID:CONTROL_IDENTITY_MATCH",errors)

    def test_ledger_reseal_invalidates_old_start(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(Path(td)); old=f.cas()
            f.reseal("ledger","ledger-v2\n")
            errors,_=identity.validate_bound_start(f.root,guard=f.guard,cas=old)
            self.assertIn("BOUND_START_IDENTITY_INVALID:CONTROL_IDENTITY_MATCH",errors)

    def test_surface_byte_change_invalidates_old_start(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(Path(td)); old=f.cas()
            f.surface["new_control_fact"]="changed"
            write(f.surface_path,f.surface)
            errors,_=identity.validate_bound_start(f.root,guard=f.guard,cas=old)
            self.assertIn("BOUND_START_IDENTITY_INVALID:CONTROL_IDENTITY_MATCH",errors)

    def test_finalizer_cannot_turn_stale_control_identity_into_success(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f=Fixture(root); old=f.cas()
            safe="protein-active-learning-trial-0"
            write(root/"RANK15_START_CAS_V4.json",old)
            write(root/"jobs"/safe/"trial"/"result.json",{"verifier_result":{"rewards":{"reward":1}}})
            f.reseal("epoch","epoch-v2\n")
            env={
                "GITHUB_WORKSPACE":str(root),
                "SAFE_ID":safe,
                "CACHE_READY":"true",
                "HARBOR_OUTCOME":"success",
                "GITHUB_RUN_ID":"synthetic",
                "GITHUB_RUN_ATTEMPT":"1",
                "GITHUB_SHA":"c"*40,
            }
            with mock.patch.dict(os.environ,env,clear=False):
                self.assertEqual(finalizer.main(),0)
            receipt=json.loads((root/(safe+"__SLOT_RECEIPT_V4.json")).read_text())
            self.assertTrue(receipt["task_started"])
            self.assertEqual(receipt["status"],"FINAL_ZERO")
            self.assertFalse(receipt["start_cas_identity_valid"])
            self.assertTrue(any("CONTROL_IDENTITY_MATCH" in x for x in receipt["errors"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
