#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V4.json"
NEW = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V5.json"
CAS = "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"
PREFLIGHT = "capsules/tb_science_rank20_20261010_v1/rank20_execution_preflight_v7.py"
ADVERSARIAL = "execution_guard/tests/test_rank20_start_cas_import_bootstrap_adversarial_v1.py"
EXPECTED_OLD_CAS = "0476919d1619c34168b25df98bcd93f6c64585ce"
EXPECTED_NEW_CAS = "50602966063a7e2c58761faa4798f5ec4f2eb0e3"
EXPECTED_OLD_PREFLIGHT = "74d55719d01f3f434b0b75001548f56a4ed83ff6"
EXPECTED_NEW_PREFLIGHT = "e6e6a8fa27f8f4def629b43612933c17f95053f6"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def main() -> int:
    old = load(OLD)
    new = load(NEW)
    for key in ("slot_id", "task_digest", "scope", "workflow_path"):
        assert old[key] == new[key], key
    assert old["behavior"] == new["behavior"]
    assert set(old["runtime_bindings"]) == set(new["runtime_bindings"])
    for key in old["runtime_bindings"]:
        if key in {"start_cas", "preflight"}:
            continue
        assert old["runtime_bindings"][key] == new["runtime_bindings"][key], key

    assert old["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_OLD_CAS
    assert new["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_NEW_CAS
    assert old["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_OLD_PREFLIGHT
    assert new["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_NEW_PREFLIGHT
    assert blob(CAS) == EXPECTED_NEW_CAS
    assert blob(PREFLIGHT) == EXPECTED_NEW_PREFLIGHT

    for row in (old, new):
        assert row["task_read"] is False
        assert row["task_started"] is False
        assert row["benchmark_trials_executed"] == 0
    assert new["execution_authority"] is False
    assert new["promotion_authority"] is False
    assert new["acceptance_credit_delta"] == 0
    assert new["terminal_credit_delta"] == 0
    assert not list((ROOT / "capsules/tb_science_rank20_20261010_v1").glob("ACTIVATE_RANK20*_PR.json"))

    for rel in (CAS, PREFLIGHT):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "execute/tb-science-rank20-20261010-v2" not in text
        assert "ACTIVATE_RANK20_V2_PR.json" not in text

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [sys.executable, str(ROOT / CAS), "--help"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr
    ns = runpy.run_path(str(ROOT / ADVERSARIAL), run_name="rank20_v5_adversarial")
    ns["test_start_cas_wrapper_bootstraps_repository_imports_without_cwd_help"]()

    compile((ROOT / PREFLIGHT).read_text(encoding="utf-8"), str(ROOT / PREFLIGHT), "exec")
    print("PASS__RANK20_V5_AUTHORITY_DERIVED_ACTIVATION_REFINEMENT__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
