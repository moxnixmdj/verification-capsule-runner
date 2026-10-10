#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V4.json"
NEW = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V5.json"
WORKFLOW = ".github/workflows/execute-tb-science-rank20-20261010-v1.yml"
CAS = "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"
PREFLIGHT = "capsules/tb_science_rank20_20261010_v1/rank20_execution_preflight_v7.py"
ZERO = "capsules/tb_science_rank20_20261010_v1/rank20_v2_zero_exposure_reseal_tests.py"

EXPECTED_WORKFLOW = "33347ec7e5424628520c863f800c05b29df05025"
EXPECTED_CAS = "ae2668664c08392ee0ed09f77303c34cbf55f91e"
EXPECTED_PREFLIGHT = "dcb7f3d87f10452a4755dbfaf6fce01f8dd270e8"
EXPECTED_ZERO = "fa2bf28ef998c900f80f1ccaff64f7153200df93"


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(rel: str):
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def main() -> int:
    old = load(OLD)
    new = load(NEW)

    assert old["slot_id"] == new["slot_id"]
    assert old["task_digest"] == new["task_digest"]
    assert old["scope"] == new["scope"]
    assert old["behavior"] == new["behavior"]
    assert old["workflow_path"] == new["workflow_path"] == WORKFLOW

    changed = {
        key for key in old["runtime_bindings"]
        if old["runtime_bindings"][key] != new["runtime_bindings"][key]
    }
    assert changed == {"zero_exposure_tests", "start_cas", "preflight"}, changed

    assert new["runtime_bindings"]["start_cas"]["git_blob_sha"] == EXPECTED_CAS
    assert new["runtime_bindings"]["preflight"]["git_blob_sha"] == EXPECTED_PREFLIGHT
    assert new["runtime_bindings"]["zero_exposure_tests"]["git_blob_sha"] == EXPECTED_ZERO

    assert blob(WORKFLOW) == EXPECTED_WORKFLOW
    assert blob(CAS) == EXPECTED_CAS
    assert blob(PREFLIGHT) == EXPECTED_PREFLIGHT
    assert blob(ZERO) == EXPECTED_ZERO

    wf = (ROOT / WORKFLOW).read_text(encoding="utf-8")
    cas = (ROOT / CAS).read_text(encoding="utf-8")
    preflight = (ROOT / PREFLIGHT).read_text(encoding="utf-8")
    zero = (ROOT / ZERO).read_text(encoding="utf-8")

    for text in (wf, cas, preflight, zero):
        assert "execute/tb-science-rank20-20261010-v3" in text or text is preflight
        assert "ACTIVATE_RANK20_V3_PR.json" in text
        assert "execute/tb-science-rank20-20261010-v2" not in text
        assert "ACTIVATE_RANK20_V2_PR.json" not in text

    assert new["task_read"] is False
    assert new["task_started"] is False
    assert new["benchmark_trials_executed"] == 0
    assert new["execution_authority"] is False
    assert new["promotion_authority"] is False

    print("PASS__RANK20_V5_FRESH_V3_IDENTITY_CLOSURE__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
