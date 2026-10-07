from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME = ROOT / "canonical/runtime/universal_escape_resolver_v1.py"
GOV = ROOT / "canonical/governance/UNIVERSAL_ESCAPE_RESOLVER_V1.json"
EXPECTED = ROOT / "EXPECTED_BRAIN_BLOBS.json"


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def install_stubs():
    canonical = types.ModuleType("canonical")
    canonical.__path__ = []
    runtime = types.ModuleType("canonical.runtime")
    runtime.__path__ = []
    canonical.runtime = runtime
    sys.modules["canonical"] = canonical
    sys.modules["canonical.runtime"] = runtime

    state = {
        "db_calls": 0,
        "source_calls": 0,
        "planner_calls": 0,
        "db_result": None,
        "source_result": None,
        "planner_result": None,
        "db_exc": None,
        "source_exc": None,
        "planner_exc": None,
    }

    db = types.ModuleType("canonical.runtime.semantic_elision_db_admission_v1")
    def db_evaluate(payload):
        state["db_calls"] += 1
        if state["db_exc"] is not None:
            raise state["db_exc"]
        return dict(state["db_result"] or {
            "pass": False,
            "db_admission_authorized": False,
            "status": "UNRESOLVED",
        })
    db.evaluate = db_evaluate

    source = types.ModuleType("canonical.runtime.source_positive_adequacy_db_admission_v1")
    def source_evaluate(payload):
        state["source_calls"] += 1
        if state["source_exc"] is not None:
            raise state["source_exc"]
        return dict(state["source_result"] or {
            "pass": False,
            "db_admission_authorized": False,
            "status": "UNRESOLVED",
        })
    source.evaluate = source_evaluate

    planner = types.ModuleType("canonical.runtime.universal_learning_meta_policy_router_v9")
    def route(**kwargs):
        state["planner_calls"] += 1
        if state["planner_exc"] is not None:
            raise state["planner_exc"]
        return dict(state["planner_result"] or {
            "route": "ABSTAIN",
            "next_action": None,
        })
    planner.route = route

    mods = {
        "semantic_elision_db_admission_v1": db,
        "source_positive_adequacy_db_admission_v1": source,
        "universal_learning_meta_policy_router_v9": planner,
    }
    for short, mod in mods.items():
        full = "canonical.runtime." + short
        sys.modules[full] = mod
        setattr(runtime, short, mod)
    return state


def load_resolver():
    state = install_stubs()
    name = "canonical.runtime.universal_escape_resolver_v1"
    spec = importlib.util.spec_from_file_location(name, RUNTIME)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod, state


def reset(state):
    for key in list(state):
        if key.endswith("_calls"):
            state[key] = 0
        else:
            state[key] = None


def verify_exact_bytes():
    manifest = json.loads(EXPECTED.read_text(encoding="utf-8"))
    for rel, expected in manifest["exact_brain_blobs"].items():
        got = git_blob_sha(ROOT / rel)
        assert got == expected, (rel, got, expected)


def verify_static_boundary():
    tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    banned_imports = {"os", "subprocess", "socket", "requests", "httpx", "urllib"}
    banned_calls = {"open", "exec", "eval", "compile", "__import__", "system", "Popen"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_imports, alias.name
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in banned_imports, node.module
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls, node.func.id

    gov = json.loads(GOV.read_text(encoding="utf-8"))
    rules = set(gov["hard_rules"])
    claims = set(gov["hard_nonclaims"])
    assert "NO_PLANNER_RESULT_IS_AN_ADMISSION_CERTIFICATE" in rules
    assert "NO_CELL_ADMISSION_WITH_IDENTITY_MISMATCH" in rules
    assert "NO_U_EMPTY_FROM_ONE_OR_ANY_NON_SCOPE_COMPLETE_SET_OF_CELL_ADMISSIONS" in rules
    assert "NO_CLAIM_U_IS_EMPTY" in claims
    assert "NO_D_FINALITY_OR_TERMINAL_CREDIT" in claims
    assert gov["accounting"]["terminal_credit_delta"] == 0


def verify_adversarial_orchestration():
    r, s = load_resolver()

    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=False,
        admission_candidates={},
        v9_args={},
    )
    assert out["pass"] is False
    assert out["reason"] == "ESCAPE_MEMBERSHIP_NOT_BOUND"
    assert s["planner_calls"] == s["db_calls"] == s["source_calls"] == 0

    reset(s)
    s["source_result"] = {
        "pass": True,
        "db_admission_authorized": True,
        "cell_id": "e1",
        "status": "PASS_SOURCE",
    }
    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=True,
        admission_candidates={
            "D_SOURCE_POSITIVE_ADEQUACY": {
                "route": "D_SOURCE_POSITIVE_ADEQUACY",
                "payload": {"cell_id": "e1"},
            }
        },
        v9_args={},
    )
    assert out["pass"] is True
    assert out["selected_admission_route"] == "D_SOURCE_POSITIVE_ADEQUACY"
    assert out["db_admission_authorized"] is True
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
    assert s["planner_calls"] == 0

    reset(s)
    s["db_result"] = {
        "pass": True,
        "db_admission_authorized": True,
        "cell_id": "e1",
        "status": "PASS_DB",
    }
    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=True,
        admission_candidates={
            "B_ROBUST_COMMON_POLICY": {
                "route": "B_ROBUST_COMMON_POLICY",
                "payload": {},
            }
        },
        v9_args={},
    )
    assert out["pass"] is True
    assert out["selected_admission_route"] == "B_ROBUST_COMMON_POLICY"
    assert s["planner_calls"] == 0

    reset(s)
    s["db_result"] = {
        "pass": True,
        "db_admission_authorized": True,
        "cell_id": "wrong-cell",
        "status": "PASS_WRONG_CELL",
    }
    s["planner_result"] = {
        "route": "LEARN",
        "next_action": {"type": "SAFE_PROBE", "id": "q"},
        "db_admission_authorized": True,
        "u_empty_authorized": True,
        "terminal_authority": True,
        "terminal_credit_delta": 999,
    }
    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=True,
        admission_candidates={
            "B_ROBUST_COMMON_POLICY": {
                "route": "B_ROBUST_COMMON_POLICY",
                "payload": {},
            }
        },
        v9_args={},
    )
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
    assert out["universal_learning_invoked"] is True
    assert out["learning_next_action"]["id"] == "q"

    reset(s)
    s["planner_result"] = {
        "route": "PROOF_SUFFICIENT_NO_EMPIRICAL_LEARNING",
        "next_action": {"type": "USE_PROOF"},
        "db_admission_authorized": True,
        "terminal_authority": True,
    }
    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=True,
        admission_candidates={},
        v9_args={},
    )
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0

    reset(s)
    s["planner_exc"] = RuntimeError("planner failed")
    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=True,
        admission_candidates={},
        v9_args={},
    )
    assert out["pass"] is False
    assert out["reason"] == "UNIVERSAL_LEARNING_PLANNER_FAILED"
    assert out["db_admission_authorized"] is False
    assert out["terminal_authority"] is False

    reset(s)
    out = r.resolve(
        escape_cell_id="e1",
        escape_membership_bound=True,
        admission_candidates={},
        v9_args={},
        admission_order=("B_ROBUST_COMMON_POLICY", "B_ROBUST_COMMON_POLICY"),
    )
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_ORDER_INVALID"
    assert s["planner_calls"] == 0



def verify_live_activation():
    activation = json.loads(
        (ROOT / "canonical/governance/UNIVERSAL_ESCAPE_RESOLVER_V2_ACTIVATION_20261007_V1.json")
        .read_text(encoding="utf-8")
    )
    authority = json.loads(
        (ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
        .read_text(encoding="utf-8")
    )

    frontier = activation["current_frontier"]
    assert frontier["git_blob_sha"] == "8ab5cd358f460ca649ec3b0ac8eea56e87d7f838"
    assert frontier["primary_roles"] == [
        "B0_INPUT_PERCEPTION_AND_GROUNDING",
        "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
        "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
        "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
    ]
    assert frontier["deferred_local_only"] == ["B9_MULTI_ROLE_COMPOSITION"]
    assert set(frontier["do_not_schedule_as_primary"]) == {
        "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
        "B3_TEMPORAL_STATE_MEMORY_AND_CONTINUITY",
        "B5_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        "B6_DELEGATION_AND_COORDINATION",
        "B8_SELF_VERIFICATION_FAILURE_LOCALIZATION_AND_RECOVERY",
    }

    regime = activation["acceptance_regime_quotient"]
    assert regime["git_blob_sha"] == "2bf5d4b28fb839028fc7a369eab53f93e8b8605c"
    assert regime["regimes"] == ["O_OBJECTIVE_ACCEPTANCE", "Q_QUALITATIVE_RELATIVE_ORDER"]

    continuity = activation["cross_run_continuity"]
    assert continuity["solver_git_blob_sha"] == "d65ebac0fdce52c9873af8da4cb69c34ef7e6206"
    assert continuity["resume_authenticator_git_blob_sha"] == "6b9d3f2c9ad2096a294d97b255798cac13262cd1"
    assert continuity["terminal_authority"] is False

    boundary = activation["authority_boundary"]
    assert boundary["planner_may_authorize_execution"] is False
    assert boundary["planner_may_authorize_db_admission"] is False
    assert boundary["planner_may_authorize_u_empty"] is False
    assert boundary["planner_may_authorize_d_finality"] is False
    assert boundary["planner_may_authorize_terminal"] is False
    assert boundary["acceptance_regime_quotient_is_scope_complete_proof"] is False
    assert boundary["only_existing_fail_closed_db_admission_can_promote_cell"] is True

    truth = activation["truth_preservation"]
    assert truth["open_abc_refinement_family_count_changed"] is False
    assert truth["u_empty_changed"] is False
    assert truth["d_finality_changed"] is False
    assert truth["terminal_changed"] is False
    assert truth["terminal_credit_delta"] == 0

    src = authority["authoritative_sources"]["universal_escape_resolver_v2_active_planning_overlay"]
    assert src["path"] == "canonical/governance/UNIVERSAL_ESCAPE_RESOLVER_V2_ACTIVATION_20261007_V1.json"
    assert src["git_blob_sha"] == "13da6cdb17122a4a8a8d97072e9886c0009f3616"
    assert src["primitive_u_frontier"]["git_blob_sha"] == "8ab5cd358f460ca649ec3b0ac8eea56e87d7f838"
    assert src["acceptance_regime_quotient"]["git_blob_sha"] == "2bf5d4b28fb839028fc7a369eab53f93e8b8605c"
    assert src["cross_run_solver"]["git_blob_sha"] == "d65ebac0fdce52c9873af8da4cb69c34ef7e6206"
    assert src["cross_run_solver"]["resume_authenticator_git_blob_sha"] == "6b9d3f2c9ad2096a294d97b255798cac13262cd1"

    live = authority["live_truth"]
    assert live["universal_escape_resolver_v2_planning_overlay_active"] is True
    assert live["universal_escape_resolver_primary_u_roles"] == frontier["primary_roles"]
    assert live["universal_escape_resolver_deferred_local_only_roles"] == ["B9_MULTI_ROLE_COMPOSITION"]
    assert live["universal_escape_resolver_acceptance_regimes"] == ["O_OBJECTIVE_ACCEPTANCE", "Q_QUALITATIVE_RELATIVE_ORDER"]
    assert live["universal_escape_resolver_acceptance_regime_quotient_scope_complete_proof"] is False
    assert live["universal_escape_resolver_db_admission_authority"] is False
    assert live["universal_escape_resolver_u_empty_authority"] is False
    assert live["universal_escape_resolver_d_finality_authority"] is False
    assert live["universal_escape_resolver_terminal_authority"] is False
    assert live["new_environment_learning_reopened_as_capability_build_problem"] is False
    assert live["universal_solver_authenticated_cross_run_resume_available"] is True

    assert live["current_U_empty_proved"] is False
    assert live["complete_selected_context_ABC_closed"] is False
    assert live["D_finality_closed"] is False
    assert live["terminal"] is False
    assert live["open_ABC_refinement_family_count"] == 13


if __name__ == "__main__":
    verify_exact_bytes()
    print("exact Brain resolver blobs: PASS")
    verify_static_boundary()
    print("static authority boundary: PASS")
    verify_adversarial_orchestration()
    print("adversarial orchestration theorem: PASS")
    verify_live_activation()
    print("four-role two-regime live activation truth-preservation theorem: PASS")
    print("UNIVERSAL ESCAPE RESOLVER V1 INDEPENDENT VERIFICATION: PASS")
