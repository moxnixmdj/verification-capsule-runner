#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V3.json"
NEW = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V4.json"
ACTIVATION = "capsules/tb_science_rank20_20261010_v1/ACTIVATE_RANK20_V2_PR.json"
CAS = "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"
EXPECTED_OLD_CAS = "35cd4c7a31d5ffbafa755dcdf888c2dee1beeb1b"
EXPECTED_NEW_CAS = "0476919d1619c34168b25df98bcd93f6c64585ce"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def main() -> int:
    old = load(OLD)
    new = load(NEW)
    assert old["slot_id"] == new["slot_id"]
    assert old["task_digest"] == new["task_digest"]
    assert old["scope"] == new["scope"]
    assert old["workflow_path"] == new["workflow_path"]
    assert old["behavior"] == new["behavior"]

    assert set(old["runtime_bindings"]) == set(new["runtime_bindings"])
    for key in old["runtime_bindings"]:
        if key == "start_cas":
            continue
        assert old["runtime_bindings"][key] == new["runtime_bindings"][key], key

    assert old["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_OLD_CAS
    assert new["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_NEW_CAS
    assert blob(CAS) == EXPECTED_NEW_CAS
    assert old["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_OLD_PREFLIGHT
    assert new["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_NEW_PREFLIGHT
    assert blob(PREFLIGHT) == EXPECTED_NEW_PREFLIGHT

    for row in (old, new):
        assert row["task_read"] is False
        assert row["task_started"] is False
        assert row["benchmark_trials_executed"] == 0
    assert new["execution_authority"] is False
    assert new["promotion_authority"] is False
    assert new["acceptance_credit_delta"] == 0
    assert new["terminal_credit_delta"] == 0
    assert not (ROOT / ACTIVATION).exists()

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

    print("PASS__RANK20_V4_IMPORT_CLOSURE_AND_AUTHORITY_DERIVED_ACTIVATION_REFINEMENT__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
