from execution_guard.terminal_execution_admission_v4 import check_decoupled_claim_binding


def _surface():
    return {
        "slot_id": "slot",
        "task_digest": "sha256:" + "1" * 64,
        "workflow_git_blob_sha": "2" * 40,
        "behavior": {"git_blob_sha": "3" * 40},
        "invariant_registry": {"git_blob_sha": "4" * 40},
    }


def _behavior(decoupled=True):
    bindings = {
        "identity_primitive": {"git_blob_sha": "5" * 40},
        "zero_exposure_tests": {"git_blob_sha": "6" * 40},
        "planner": {"git_blob_sha": "7" * 40},
        "agent": {"git_blob_sha": "8" * 40},
    }
    if decoupled:
        bindings["claim_bound_identity_resolver"] = {"git_blob_sha": "9" * 40}
    return {"runtime_bindings": bindings}


def _claim():
    return {
        "slot_id": "slot",
        "task_digest": "sha256:" + "1" * 64,
        "workflow_blob": "2" * 40,
        "behavior_blob": "3" * 40,
        "invariant_registry_blob": "4" * 40,
        "identity_v2_blob": "5" * 40,
        "zero_exposure_test_blob": "6" * 40,
        "planner_v7_blob": "7" * 40,
        "agent_v13_blob": "8" * 40,
        "claim_bound_identity_resolver_blob": "9" * 40,
    }


def test_decoupled_claim_binding_exact_match():
    errors = []
    check_decoupled_claim_binding(_surface(), _behavior(), _claim(), errors)
    assert errors == []


def test_decoupled_claim_binding_behavior_mismatch_fails_closed():
    claim = _claim()
    claim["behavior_blob"] = "a" * 40
    errors = []
    check_decoupled_claim_binding(_surface(), _behavior(), claim, errors)
    assert errors == ["DECOUPLED_CLAIM_BINDING_MISMATCH:behavior_blob"]


def test_legacy_behavior_is_not_forced_through_decoupled_validator():
    errors = []
    claim = _claim()
    claim["behavior_blob"] = "a" * 40
    check_decoupled_claim_binding(_surface(), _behavior(decoupled=False), claim, errors)
    assert errors == []
