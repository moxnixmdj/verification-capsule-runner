#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/runtime/atomic_terminal_execution_authority_deriver_v1.py": "df069b6a4873a21582dbc7eed98c4729580542f2",
    "canonical/tests/test_atomic_terminal_execution_authority_deriver_v1.py": "bef8d274f6eefe8ea2f3446cc114b53d43afba33",
    "canonical/verification/ATOMIC_ROUTE_SPECIFIC_TERMINAL_LAUNCH_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "3221f7ad906114e69f0a491fc84114f02db397f5",
    "canonical/runtime/atomic_route_specific_terminal_launch_v1.py": "b042d04a43cc2866744c01d30a447bd47a21dddc",
    "canonical/tests/test_atomic_route_specific_terminal_launch_v1.py": "46036b35e5e912f13c2b7adc94a6809b924b9135",
    "canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json": "621f41ccc22688b31d364e895bc62449b5c7e2be",
    "canonical/runtime/terminal_prequalification_reducer.py": "da929015fafabed2b5a134a2e95b6bff2f47349c",
    "canonical/tests/test_terminal_prequalification_reducer.py": "9b09e96c9bf0340d174b4a752148c0807be9043e",
    "canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json": "5d20073180fdcfd6e36145f4c820271eb1ee275f",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "afa00109031d638fef32cc3fe10be18786605c39",
    "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json": "1d905389d395ab67dbb7e6e1290e741ab3cb44cb",
    "canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json": "d1dc7f28738ba24a3ca5919755e03190fbf30939",
    "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json": "832a10cfbb2de362370ec0eee8ccedc86f52aeb3",
    "canonical/verification/SACCR_ROUTE_SPECIFIC_TERMINAL_EXECUTOR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "17835ede636462fe47ce9104521650627bdeb1a4",
    "canonical/verification/CURRENT_EXECUTOR_SNAPSHOT_V3_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "f8aac465750ab4b2618e470e163207ddcc6ac272",
    "canonical/verification/DIRECT_ROUTE_TERMINAL_EXECUTORS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json": "a1b23e9c35a8be1dce5cec6de7f25685aca803dc",
    "canonical/verification/CAD_T0_ROUTE_SPECIFIC_TERMINAL_EXECUTOR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "cc1c8997498881eb86494353ea98164bc0a03a83",
}


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_manifest_receipts():
    manifest = load_json("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json")
    assert manifest["route_count"] == 12
    assert manifest["bound_executor_count"] == 12
    routes = manifest["routes"]
    assert len(routes) == 12
    ids = {row["behavior_id"] for row in routes}
    assert len(ids) == 12
    for row in routes:
        receipt_path = row.get("independent_executor_verification") or row.get("executor_independent_verification")
        assert receipt_path, row["behavior_id"]
        receipt = load_json(receipt_path)
        assert str(receipt.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), row["behavior_id"]
        exact = receipt.get("exact_brain_blobs")
        assert isinstance(exact, dict)
        assert exact.get(row["executor"]) == row["executor_blob_sha"], row["behavior_id"]
        assert exact.get(row["tests"]) == row["executor_test_blob_sha"], row["behavior_id"]
    return ids


def install_deriver_import_environment(prequal, commitment_value: str):
    canonical = types.ModuleType("canonical")
    canonical.__path__ = []
    runtime = types.ModuleType("canonical.runtime")
    runtime.__path__ = []
    sys.modules["canonical"] = canonical
    sys.modules["canonical.runtime"] = runtime

    prequal_mod = types.ModuleType("canonical.runtime.terminal_prequalification_reducer")
    prequal_mod.evaluate = prequal.evaluate
    sys.modules[prequal_mod.__name__] = prequal_mod

    launch_mod = types.ModuleType("canonical.runtime.atomic_route_specific_terminal_launch_v1")
    launch_mod.build_prelaunch_commitment = lambda root: {
        "pass": True,
        "candidate_package_commitment": commitment_value,
        "executor_state": {"derived_bound_executor_count": 12},
        "terminal_case_generation_performed": False,
        "errors": [],
    }
    sys.modules[launch_mod.__name__] = launch_mod
    return launch_mod


def main():
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        assert path.is_file(), rel
        got = git_blob(path)
        assert got == expected, (rel, got, expected)

    compile(
        (ROOT / "canonical/runtime/atomic_terminal_execution_authority_deriver_v1.py").read_text(encoding="utf-8"),
        "atomic_terminal_execution_authority_deriver_v1.py",
        "exec",
    )
    compile(
        (ROOT / "canonical/tests/test_atomic_terminal_execution_authority_deriver_v1.py").read_text(encoding="utf-8"),
        "test_atomic_terminal_execution_authority_deriver_v1.py",
        "exec",
    )

    prequal = load_module(
        "capsule_prequalification",
        ROOT / "canonical/runtime/terminal_prequalification_reducer.py",
    )
    pre = prequal.evaluate(ROOT)
    assert pre["pass"] is True, pre
    assert pre["execution_authority"] is True
    assert pre["failed_predicates"] == []

    ids = verify_manifest_receipts()

    launch_receipt = load_json(
        "canonical/verification/ATOMIC_ROUTE_SPECIFIC_TERMINAL_LAUNCH_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
    )
    assert str(launch_receipt["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert launch_receipt["public_verifier"]["conclusion"] == "success"
    assert launch_receipt["terminal_results_observed"] == 0
    assert launch_receipt["fresh_terminal_evidence_consumed"] == 0
    exact = launch_receipt["exact_brain_blobs"]
    for rel in (
        "canonical/runtime/atomic_route_specific_terminal_launch_v1.py",
        "canonical/tests/test_atomic_route_specific_terminal_launch_v1.py",
        "canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json",
    ):
        assert exact[rel] == git_blob(ROOT / rel)

    plan = load_json("canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json")
    assert plan["counts"]["total_contracts"] == 12
    assert plan["launch_authority"] is False
    assert plan["terminal_case_generation_allowed"] is False

    basis = load_json("canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json")
    assert basis["active_contract_count"] == 12
    assert basis["admissible_frozen_terminal_route_count"] == 12
    assert all(row["proof_state"] == "TERMINAL_ROUTE_FROZEN_ADMISSIBLE" for row in basis["contracts"])
    assert all(row.get("blockers") == [] for row in basis["contracts"])

    commitment_value = hashlib.sha256(
        (
            EXPECTED["canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"]
            + EXPECTED["canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json"]
            + EXPECTED["canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json"]
        ).encode()
    ).hexdigest()

    launch_stub = install_deriver_import_environment(prequal, commitment_value)
    deriver = load_module(
        "atomic_authority_deriver_under_test",
        ROOT / "canonical/runtime/atomic_terminal_execution_authority_deriver_v1.py",
    )

    receipt_check = deriver.validate_launcher_receipt(ROOT)
    assert receipt_check["pass"] is True, receipt_check

    verdict = deriver.evaluate(ROOT)
    assert verdict["pass"] is True, verdict
    assert verdict["execution_authority"] is True
    assert verdict["authorization"] == "ATOMIC_V2_ROUTE_SPECIFIC_T0_T1_T2_T3_TERMINAL_WAVE"
    assert verdict["derived_bound_executor_count"] == 12
    assert verdict["candidate_package_commitment"] == commitment_value
    assert verdict["post_freeze_beacon_constructed"] is False
    assert verdict["terminal_results_observed"] == 0
    assert verdict["fresh_terminal_evidence_consumed"] == 0
    assert verdict["promotion_authority"] is False

    launch_stub.build_prelaunch_commitment = lambda root: {
        "pass": False,
        "candidate_package_commitment": None,
        "executor_state": {"derived_bound_executor_count": 12},
        "terminal_case_generation_performed": False,
        "errors": ["SIMULATED_DRIFT"],
    }
    blocked = deriver.evaluate(ROOT)
    assert blocked["pass"] is False
    assert blocked["execution_authority"] is False
    assert "ATOMIC_PRELAUNCH_COMMITMENT_NOT_PASS" in blocked["failed_predicates"]

    print(json.dumps({
        "status": "INDEPENDENT_PUBLIC_AUTHORITY_DERIVATION_PASS",
        "active_contract_count": len(ids),
        "execution_authority": True,
        "authorization": "ATOMIC_V2_ROUTE_SPECIFIC_T0_T1_T2_T3_TERMINAL_WAVE",
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "verified": [
            "EXACT_CURRENT_PREQUALIFICATION_BLOBS",
            "CURRENT_NONCIRCULAR_PREQUALIFICATION_PASS",
            "EXACT_12_OF_12_EXECUTOR_MANIFEST_AND_RECEIPTS",
            "EXACT_INDEPENDENT_ATOMIC_LAUNCHER_RECEIPT",
            "AUTHORITY_IS_DERIVED_NOT_TRUSTED_FROM_STALE_BOOLEAN",
            "PRELAUNCH_DRIFT_REVOKES_AUTHORITY",
            "ZERO_TERMINAL_CASES_CONSUMED",
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
