#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V4.json"
NEW = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V5.json"
CAS = "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"
PREFLIGHT = "capsules/tb_science_rank20_20261010_v1/rank20_execution_preflight_v7.py"
GATE_TEST = "execution_guard/tests/test_rank20_generation_neutral_gate_v1.py"
EXPECTED_OLD_CAS = "50602966063a7e2c58761faa4798f5ec4f2eb0e3"
EXPECTED_NEW_CAS = "99d81c7d1316d1767c688e12c2c05790c69662f3"
EXPECTED_OLD_PREFLIGHT = "e6e6a8fa27f8f4def629b43612933c17f95053f6"
EXPECTED_NEW_PREFLIGHT = "3cc62699388993a053969b03d09343c0e8a4d659"
EXPECTED_GATE_TEST = "692cdbc626ea1d7f77f71487e04f84a8e18e2343"


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
    changed = {"start_cas", "preflight"}
    for key in old["runtime_bindings"]:
        if key in changed:
            continue
        assert old["runtime_bindings"][key] == new["runtime_bindings"][key], key

    assert old["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_OLD_CAS
    assert new["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_NEW_CAS
    assert old["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_OLD_PREFLIGHT
    assert new["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_NEW_PREFLIGHT
    assert blob(CAS) == EXPECTED_NEW_CAS
    assert blob(PREFLIGHT) == EXPECTED_NEW_PREFLIGHT
    assert blob(GATE_TEST) == EXPECTED_GATE_TEST

    for row in (old, new):
        assert row["task_read"] is False
        assert row["task_started"] is False
        assert row["benchmark_trials_executed"] == 0
    assert new["execution_authority"] is False
    assert new["promotion_authority"] is False
    assert new["acceptance_credit_delta"] == 0
    assert new["terminal_credit_delta"] == 0

    for name in ("ACTIVATE_RANK20_V2_PR.json", "ACTIVATE_RANK20_V3_PR.json"):
        assert not (ROOT / "capsules/tb_science_rank20_20261010_v1" / name).exists()

    proc = subprocess.run(
        [sys.executable, str(ROOT / GATE_TEST)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    print("PASS__RANK20_V5_GENERATION_NEUTRAL_GATE_REFINEMENT__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
