#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_RECEIPT = ROOT / "unknown_domain_v7_reachable_domain_receipt.json"
EXPECTED_SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_V7_REACHABLE_DOMAIN_INDEPENDENT_VERIFICATION_V1"
EXPECTED_STATUS = "PASS__CONTENT_BOUND_FROZEN_LAUNCHER_REACHABLE_TYPE_DOMAIN__CLASS_SPOOF_REJECTED__54_NONPRODUCTION_CASES__ZERO_TERMINAL_REALITY"


def run_checked(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, choices=("py312", "py313"))
    ap.add_argument("--version-prefix", required=True)
    ns = ap.parse_args()

    actual = platform.python_version()
    if not actual.startswith(ns.version_prefix):
        raise AssertionError(f"PYTHON_VERSION_MISMATCH:{actual}:{ns.version_prefix}")

    target = ROOT / f"unknown_domain_v7_reachable_domain_receipt_{ns.tag}.json"
    for p in (BASE_RECEIPT, target):
        p.unlink(missing_ok=True)

    run_checked([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "pytest==8.4.2"])
    run_checked([sys.executable, "verification/unknown_domain_v7_reachable_domain_independent_v3.py"])
    if not BASE_RECEIPT.is_file():
        raise AssertionError("FRESH_BASE_RECEIPT_MISSING")

    run_checked([sys.executable, "-m", "pytest", "-q", "canonical/tests/test_unknown_domain_direct_v5.py"])

    data = json.loads(BASE_RECEIPT.read_text(encoding="utf-8"))
    assert data["schema"] == EXPECTED_SCHEMA
    assert data["status"] == EXPECTED_STATUS
    assert data["acceptance_credit_delta"] == 0
    assert data["family_credit_delta"] == 0
    assert data["capability_credit_delta"] == 0
    assert data["ownership_credit_delta"] == 0
    assert data["launcher_boundary"]["production_or_terminal_cases_actually_generated"] == 0
    assert data["nonproduction_exact_scorer_cases"] == 54

    shutil.copyfile(BASE_RECEIPT, target)
    BASE_RECEIPT.unlink()
    if not target.is_file():
        raise AssertionError("RUNTIME_RECEIPT_COPY_FAILED")
    print(json.dumps({"status": "PASS", "runtime": actual, "receipt": target.name}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
