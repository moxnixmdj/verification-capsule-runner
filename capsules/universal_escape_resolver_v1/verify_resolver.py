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
        (ROOT / "canonical/governance/UNIVERSAL_ESCAPE_RESOLVER_V3_ACCEPTANCE_RELATION_ACTIVATION_20261007_V1.json")
        .read_text(encoding="utf-8")
    )
    authority = json.loads(
        (ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
        .read_text(encoding="utf-8")
    )
    normal = json.loads(
        (ROOT / "canonical/governance/ACCEPTANCE_RELATION_UNCERTAINTY_NORMAL_FORM_20261007_V1.json")
        .read_text(encoding="utf-8")
    )

    assert normal["status"] == "PROVED_LOGICAL_REDUCTION__O_AND_Q_COLLAPSE_TO_ONE_ACCEPTANCE_UNCERTAINTY_PRIMITIVE__ZERO_CREDIT"
    assert normal["wolfram_check"] == {
        "general_implication": True,
        "singleton_objective_special_case": True,
        "multi_relation_quality_special_case": True,
    }
    assert "R_STAR_IS_IN_R_OVER" in normal["theorem"]
    assert "FOR_EVERY_R_IN_R_OVER" in normal["theorem"]

    ar = activation["acceptance_relation_normal_form"]
    assert ar["git_blob_sha"] == "42498bbe40327cd47be5e4251e7f524a8c0c8d5b"
    assert ar["R_STAR"].startswith("ACTUAL_LOAD_BEARING_TARGET_ACCEPTANCE")
    assert ar["R_OVER"].startswith("SOUND_OVERAPPROXIMATION")
    assert "MINIMUM_TRUTHFUL_INFORMATION" in ar["refinement_rule"]

    ul = activation["universal_learning_role"]
    assert ul["new_environment_learning_reopened_as_build_problem"] is False
    assert ul["self_certification_authority"] is False
    assert "MINIMUM_DECISION_OR_POLICY_ADEQUACY_CHANGING" in ul["objective"]

    solver = activation["solver_execution_chain"]
    assert solver["solver_git_blob_sha"] == "659cda15bb956606a023cc9495e4036ce13e19d9"
    assert solver["resume_authenticator_git_blob_sha"] == "6b9d3f2c9ad2096a294d97b255798cac13262cd1"
    assert solver["episode_verification_authenticator_git_blob_sha"] == "6a2fc8f26d1908eb7a35006f3a550fe2cd55c171"
    assert solver["skill_verification_authenticator_git_blob_sha"] == "aa1925d9192f5bba6e65d32c9319397e03b02e6c"

    astra = activation["astra_bound_subplan_proposal_source"]
    assert astra["carrier_git_blob_sha"] == "3333e933af779f0de8d833f7c84e1507887b1343"
    assert astra["semantic_effect_authority"] is False
    assert astra["db_admission_authority"] is False
    assert astra["terminal_authority"] is False
    assert "PROPOSAL" in astra["admitted_use"]

    boundary = activation["authority_boundary"]
    assert boundary["planner_may_authorize_execution"] is False
    assert boundary["planner_may_authorize_db_admission"] is False
    assert boundary["planner_may_authorize_u_empty"] is False
    assert boundary["planner_may_authorize_d_finality"] is False
    assert boundary["planner_may_authorize_terminal"] is False
    assert boundary["acceptance_relation_reduction_grants_cell_credit"] is False
    assert boundary["astra_carrier_grants_semantic_effect_authority"] is False
    assert boundary["only_existing_fail_closed_db_admission_can_promote_cell"] is True

    src = authority["authoritative_sources"]["universal_escape_resolver_v3_acceptance_relation_overlay"]
    assert src["git_blob_sha"] == "ee77bf0584095a39a2aeceb014462aaf5860aec2"
    assert src["acceptance_relation_normal_form"]["git_blob_sha"] == "42498bbe40327cd47be5e4251e7f524a8c0c8d5b"
    assert src["universal_solver"]["git_blob_sha"] == "659cda15bb956606a023cc9495e4036ce13e19d9"
    assert src["astra_bound_subplan_carrier"]["git_blob_sha"] == "3333e933af779f0de8d833f7c84e1507887b1343"
    assert src["astra_bound_subplan_carrier"]["semantic_effect_authority"] is False
    assert src["astra_bound_subplan_carrier"]["db_admission_authority"] is False
    assert src["astra_bound_subplan_carrier"]["terminal_authority"] is False

    live = authority["live_truth"]
    assert live["universal_escape_resolver_v3_acceptance_relation_overlay_active"] is True
    assert live["universal_escape_resolver_v2_planning_overlay_active"] is False
    assert live["universal_escape_resolver_primary_terminal_proof_primitive"] == "SOUND_ACCEPTANCE_RELATION_OVERAPPROXIMATION_PLUS_COMMON_POSITIVE_ADEQUACY"
    assert live["universal_escape_resolver_acceptance_relation_symbol"] == "R_OVER"
    assert live["universal_escape_resolver_actual_acceptance_relation_symbol"] == "R_STAR"
    assert live["universal_escape_resolver_O_Q_split_superseded_for_primary_scheduling"] is True
    assert live["universal_escape_resolver_O_Q_preserved_as_special_cases"] is True
    assert live["astra_bound_subplan_carrier_available_as_proposal_source"] is True
    assert live["astra_bound_subplan_carrier_semantic_effect_authority"] is False
    assert live["astra_bound_subplan_carrier_db_admission_authority"] is False
    assert live["astra_bound_subplan_carrier_terminal_authority"] is False

    order = live["current_escape_planning_order"]
    assert order[0] == "SELECT_BOUND_ESCAPE_CELL_IN_B0_B2_B4_OR_B7"
    assert order[1] == "BIND_SOUND_R_OVER_CONTAINING_R_STAR"
    assert "IF_COMMON_POLICY_PROVED_SUBMIT_TO_EXISTING_FAIL_CLOSED_D_B_ADMISSION" in order
    assert "IF_UNRESOLVED_USE_UNIVERSAL_LEARNING_FOR_MINIMUM_POLICY_CHANGING_INFORMATION_OR_MISSING_MECHANISM_ONLY" in order
    assert "ALLOW_VERIFIED_ASTRA_BOUND_SUBPLAN_CARRIER_AS_PROPOSAL_SOURCE_WHEN_APPLICABLE_WITH_ZERO_SEMANTIC_AUTHORITY" in order

    assert live["current_U_empty_proved"] is False
    assert live["complete_selected_context_ABC_closed"] is False
    assert live["D_finality_closed"] is False
    assert live["terminal"] is False


if __name__ == "__main__":
    verify_exact_bytes()
    print("exact Brain resolver blobs: PASS")
    verify_static_boundary()
    print("static authority boundary: PASS")
    verify_adversarial_orchestration()
    print("adversarial orchestration theorem: PASS")
    verify_live_activation()
    print("single acceptance-relation live activation truth-preservation theorem: PASS")
    print("UNIVERSAL ESCAPE RESOLVER V1 INDEPENDENT VERIFICATION: PASS")
