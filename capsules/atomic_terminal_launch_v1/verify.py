#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAUNCHER = ROOT / "canonical/runtime/atomic_route_specific_terminal_launch_v1.py"
TESTS = ROOT / "canonical/tests/test_atomic_route_specific_terminal_launch_v1.py"
PLAN_COPY = ROOT / "canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json"

EXPECTED = {
    LAUNCHER: "b042d04a43cc2866744c01d30a447bd47a21dddc",
    TESTS: "46036b35e5e912f13c2b7adc94a6809b924b9135",
    PLAN_COPY: "621f41ccc22688b31d364e895bc62449b5c7e2be",
}

CAD = "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
SACCR = "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"
BROWSER = "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001"
DELEGATION = "TASK_TO_DELEGATION_GRAPH_001"
TOOL = "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
RESEARCH = "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001"
M0 = "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
NATIVE = "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001"
STRUCTURED = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"

PARENTS = {
    M0: {"T0", "T1", "T2", "T3"},
    STRUCTURED: {"T0", "T1"},
    P1: {"T0", "T2"},
    P2: {"T1"},
    NATIVE: {"T1"},
    P3: {"T1", "T3"},
}
BINDINGS = {bid: {"binding_blob": hashlib.sha1(bid.encode()).hexdigest()} for bid in PARENTS}


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def install_stubs():
    canonical = types.ModuleType("canonical")
    canonical.__path__ = []
    runtime = types.ModuleType("canonical.runtime")
    runtime.__path__ = []
    sys.modules["canonical"] = canonical
    sys.modules["canonical.runtime"] = runtime

    cad = types.ModuleType("canonical.runtime.cad_t0_route_specific_terminal_executor_v1")
    def no_cad(*args, **kwargs):
        raise AssertionError("CAD terminal execution must not occur in shadow verification")
    cad.execute_cad_route = no_cad
    sys.modules[cad.__name__] = cad

    direct = types.ModuleType("canonical.runtime.direct_route_terminal_executors_v1")
    direct.BROWSER_ID = BROWSER
    direct.DELEGATION_ID = DELEGATION
    direct.TOOL_ID = TOOL
    direct.RESEARCH_ID = RESEARCH
    def no_direct(*args, **kwargs):
        raise AssertionError("direct terminal execution must not occur in shadow verification")
    direct.execute_direct_route = no_direct
    sys.modules[direct.__name__] = direct

    multiplex = types.ModuleType("canonical.runtime.portfolio_multiplex_terminal_instrumentation_v1")
    multiplex.M0 = M0
    multiplex.NATIVE = NATIVE
    multiplex.STRUCTURED = STRUCTURED
    multiplex.P2 = P2
    multiplex.P3 = P3
    multiplex.P1 = P1
    multiplex.BINDINGS = BINDINGS

    def reduce_behavior_receipts(bid, rows):
        errors = []
        for row in rows:
            if row.get("behavior_id") != bid:
                errors.append("BEHAVIOR")
            if row.get("binding_blob") != BINDINGS[bid]["binding_blob"]:
                errors.append("BINDING")
            if row.get("case_replaced") is not False:
                errors.append("REPLACED")
            if row.get("tuning_replay") is not False:
                errors.append("REPLAY")
            if row.get("result_to_runtime_feedback") is not False:
                errors.append("FEEDBACK")
            if row.get("direct_instrumentation_pass") is not True:
                errors.append("DIRECT")
            if row.get("parent_terminal_acceptance_pass") is not True:
                errors.append("PARENT")
            if "hidden_oracle" in set(row.get("candidate_visible_keys") or []):
                errors.append("LEAK")
        return {"status": "PASS_COMPONENT" if not errors else "FAIL_CLOSED", "errors": errors}

    multiplex.reduce_behavior_receipts = reduce_behavior_receipts
    sys.modules[multiplex.__name__] = multiplex

    saccr = types.ModuleType("canonical.runtime.saccr_route_specific_terminal_executor_v1")
    def no_saccr(*args, **kwargs):
        raise AssertionError("SA-CCR terminal execution must not occur in shadow verification")
    saccr.execute_terminal = no_saccr
    sys.modules[saccr.__name__] = saccr

    pv = types.ModuleType("canonical.runtime.terminal_route_execution_plan_validator")
    pv.validate = lambda root, plan: {
        "pass": True,
        "validated_contract_count": 12,
        "terminal_case_generation_performed": False,
    }
    sys.modules[pv.__name__] = pv


def load_launcher():
    install_stubs()
    spec = importlib.util.spec_from_file_location("atomic_launcher_under_test", LAUNCHER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture(mod, root: Path):
    # Minimal content-addressed universe for integration logic.  The real frozen
    # execution graph is independently checked below from the copied exact plan.
    write_json(root / mod.PLAN, {"schema": "FIXTURE_PLAN"})
    write_json(root / mod.PROTOCOL, {"active_contracts": sorted(mod.EXPECTED_IDS)})
    write_json(root / mod.SELECTION_KERNEL, {"schema": "FIXTURE_SELECTION"})
    write_json(root / mod.AUTHORITY, {
        "execution_authority": False,
        "authorization": "NONE",
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
    })

    rows = []
    for i, bid in enumerate(sorted(mod.EXPECTED_IDS)):
        executor = f"canonical/runtime/executor_{i}.py"
        tests = f"canonical/tests/test_executor_{i}.py"
        receipt = f"canonical/verification/receipt_{i}.json"
        ep = root / executor
        tp = root / tests
        ep.parent.mkdir(parents=True, exist_ok=True)
        tp.parent.mkdir(parents=True, exist_ok=True)
        ep.write_text(f"# executor {bid}\n", encoding="utf-8")
        tp.write_text(f"# test {bid}\n", encoding="utf-8")
        esha = git_blob(ep)
        tsha = git_blob(tp)
        write_json(root / receipt, {
            "status": "INDEPENDENT_PUBLIC_RUNNER_PASS__FIXTURE",
            "exact_brain_blobs": {executor: esha, tests: tsha},
        })
        rows.append({
            "behavior_id": bid,
            "executor": executor,
            "tests": tests,
            "executor_blob_sha": esha,
            "executor_test_blob_sha": tsha,
            "independent_executor_verification": receipt,
        })
    write_json(root / mod.MANIFEST, {
        "route_count": 12,
        "bound_executor_count": 12,
        "launch_authority": False,
        "routes": rows,
    })


def good_parent_rows(mod, commitment: str, beacon: str):
    rows = {}
    for bid in sorted(mod.MULTIPLEX_IDS):
        rows[bid] = []
        for parent in sorted(mod.REQUIRED_MULTIPLEX_PARENTS[bid]):
            rows[bid].append({
                "behavior_id": bid,
                "portfolio": parent,
                "case_id": f"{parent}::case::0",
                "candidate_package_commitment": commitment,
                "post_freeze_beacon": beacon,
                "binding_blob": BINDINGS[bid]["binding_blob"],
                "load_bearing": True,
                "direct_instrumentation_pass": True,
                "parent_terminal_acceptance_pass": True,
                "case_replaced": False,
                "tuning_replay": False,
                "result_to_runtime_feedback": False,
                "candidate_visible_keys": ["public_task"],
                "claims_behavior_credit": False,
            })
    return rows


def main():
    # Exact Brain branch copies.
    for path, expected in EXPECTED.items():
        got = git_blob(path)
        assert got == expected, (path, got, expected)

    # Syntax and frozen execution-graph invariants.
    compile(LAUNCHER.read_text(encoding="utf-8"), str(LAUNCHER), "exec")
    compile(TESTS.read_text(encoding="utf-8"), str(TESTS), "exec")
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "terminal_replacement_wave" not in source
    assert "generate_post_freeze(" not in source
    assert "validate_parent_observations" in source
    assert "derive_executor_state" in source
    assert "build_prelaunch_commitment" in source

    plan = json.loads(PLAN_COPY.read_text(encoding="utf-8"))
    assert plan["counts"] == {
        "direct_population_contracts": 6,
        "multiplex_instrumentation_contracts": 6,
        "total_contracts": 12,
    }
    assert plan["launch_authority"] is False
    assert plan["terminal_case_generation_allowed"] is False
    cad = next(x for x in plan["direct_populations"] if x["behavior_id"] == CAD)
    assert cad["sample_count"] == 128
    assert cad["binding"] == {
        "path": "canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V4.json",
        "blob_sha": "a636d1292e6f92d240fab420a9ee75ced7a05104",
    }
    counts = {x["behavior_id"]: x["sample_count"] for x in plan["direct_populations"]}
    assert counts[SACCR] == 2000
    assert counts[BROWSER] == 150
    assert counts[DELEGATION] == 132
    assert counts[TOOL] == 180
    assert counts[RESEARCH] == 180
    assert {x["behavior_id"] for x in plan["multiplex_instrumentation"]} == set(PARENTS)

    mod = load_launcher()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture(mod, root)

        one = mod.build_prelaunch_commitment(root)
        two = mod.build_prelaunch_commitment(root)
        assert one["pass"] is True, one
        assert one["candidate_package_commitment"] == two["candidate_package_commitment"]
        assert one["executor_state"]["derived_bound_executor_count"] == 12
        assert one["terminal_case_generation_performed"] is False

        shadow = mod.shadow_preflight(root)
        assert shadow["pass"] is False
        assert shadow["status"] == "PRELAUNCH_NOT_AUTHORIZED"
        assert shadow["derived_bound_executor_count"] == 12
        assert shadow["terminal_case_generation_performed"] is False
        assert shadow["terminal_results_observed"] == 0

        c = one["candidate_package_commitment"]
        b = "TEST_ONLY_POST_FREEZE_BEACON"
        parents = good_parent_rows(mod, c, b)
        ok = mod.validate_parent_observations(parents, commitment=c, beacon=b)
        assert ok["pass"] is True, ok

        missing = good_parent_rows(mod, c, b)
        missing[M0] = [x for x in missing[M0] if x["portfolio"] != "T3"]
        bad = mod.validate_parent_observations(missing, commitment=c, beacon=b)
        assert bad["pass"] is False
        assert any(x.startswith("MISSING_LOAD_BEARING_PARENT_COVERAGE:") for x in bad["errors"])

        replay = good_parent_rows(mod, c, b)
        replay[M0][0]["tuning_replay"] = True
        bad = mod.validate_parent_observations(replay, commitment=c, beacon=b)
        assert bad["pass"] is False
        assert "MULTIPLEX_REDUCTION_FAIL:" + M0 in bad["errors"]

        # Critical safety property: authority=false must refuse before any direct
        # terminal executor stub can be reached.
        refused = mod.execute_real(
            commitment=c,
            beacon=b,
            parent_observations=parents,
            root=root,
        )
        assert refused["pass"] is False
        assert refused["status"] == "FAIL_CLOSED_PRELAUNCH_NOT_AUTHORIZED"
        assert refused["terminal_results_observed"] == 0

    print(json.dumps({
        "status": "INDEPENDENT_PUBLIC_CAPSULE_PASS",
        "exact_brain_blobs": {
            "canonical/runtime/atomic_route_specific_terminal_launch_v1.py": EXPECTED[LAUNCHER],
            "canonical/tests/test_atomic_route_specific_terminal_launch_v1.py": EXPECTED[TESTS],
            "canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json": EXPECTED[PLAN_COPY],
        },
        "verified": [
            "EXACT_ATOMIC_LAUNCHER_BLOB",
            "EXACT_LAUNCHER_TEST_BLOB",
            "EXACT_CAD_V4_REPINNED_EXECUTION_PLAN_BLOB",
            "SIX_DIRECT_AND_SIX_MULTIPLEX_EXACT_COVERAGE",
            "FROZEN_ROUTE_SAMPLE_COUNTS_PRESERVED",
            "CONTENT_ADDRESSED_EXECUTOR_RECEIPT_DERIVATION",
            "DETERMINISTIC_PRELAUNCH_COMMITMENT",
            "MISSING_PARENT_COVERAGE_FAILS_CLOSED",
            "TUNING_REPLAY_FAILS_CLOSED",
            "AUTHORITY_FALSE_TOUCHES_ZERO_TERMINAL_EXECUTORS",
            "ZERO_TERMINAL_CASES_CONSUMED",
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
