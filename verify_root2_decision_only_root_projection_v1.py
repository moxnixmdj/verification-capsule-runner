#!/usr/bin/env python3
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject/root2_decision_only_root_projection_v1"
ROOT_STATE = SUB / "TERMINAL_ROOT_CAUSE_STATE_V1.json"
ACT = SUB / "ROOT2_DECISION_ONLY_EVALUATION_ACTIVATION_V1.json"
REC = SUB / "ROOT2_DECISION_ONLY_EVALUATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

def git_blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def main():
    assert git_blob_sha(ROOT_STATE) == "822d7a0e64b2e919a873526d111e7202c40e1f5b"
    assert git_blob_sha(ACT) == "4086abe4559e30ade7bb7fa5be5571eaf40e94ee"
    assert git_blob_sha(REC) == "345ad6ce5d5ba5105c82e5663fa9a97e99ccec05"

    root = json.loads(ROOT_STATE.read_text())
    act = json.loads(ACT.read_text())
    rec = json.loads(REC.read_text())

    assert root["current_acceptance"] == {
        "accepted_families": 5,
        "open_families": 14,
        "proved_atomic": 12,
        "unresolved_atomic": 26,
        "total_families": 19,
        "total_atomic": 38,
        "terminal": False,
    }

    overlay = root["scheduler_policy"]["root2_decision_only_evaluation"]
    assert overlay["activation_git_blob_sha"] == git_blob_sha(ACT)
    assert overlay["verification_git_blob_sha"] == git_blob_sha(REC)
    assert overlay["subject_runtime_git_blob_sha"] == "bb70267e0bb44830a0c73708e3d4a07daecfdfa0"
    assert overlay["scheduling_authority"] is True
    assert overlay["decision_certificate_compilation"] is True
    assert overlay["execution_authority"] is False
    assert overlay["promotion_authority"] is False
    assert overlay["fresh_reality_authority"] is False
    assert overlay["acceptance_credit_delta"] == 0
    assert overlay["root_projection_verification_path"] == "canonical/verification/ROOT2_DECISION_ONLY_ROOT_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

    assert act["authority"]["scheduling"] is True
    assert act["authority"]["execution"] is False
    assert act["authority"]["fresh_reality"] is False
    assert act["authority"]["promotion"] is False
    assert act["authority"]["acceptance_reduction"] is False
    assert act["accounting"]["acceptance_credit_delta"] == 0

    assert rec["status"] == "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_DECISION_ONLY_COMPOSITION__ZERO_CREDIT"
    assert rec["independent_runner"]["workflow_run_id"] == 37190555353
    assert rec["independent_runner"]["conclusion"] == "success"

    assert root["accounting"]["acceptance_credit_delta"] == 0
    assert root["accounting"]["new_reality_units_consumed"] == 0
    assert root["accounting"]["incremental_spend_usd"] == 0

    print(json.dumps({
        "schema": "PROJECT_BRAIN_ROOT2_DECISION_ONLY_ROOT_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V1",
        "status": "PASS__EXACT_ROOT_PROJECTION__SCHEDULING_ONLY__ZERO_CREDIT",
        "root_state_blob": git_blob_sha(ROOT_STATE),
        "activation_blob": git_blob_sha(ACT),
        "receipt_blob": git_blob_sha(REC),
        "accepted_families": 5,
        "proved_atomic": 12,
        "unresolved_atomic": 26,
        "scheduling_authority": True,
        "execution_authority": False,
        "fresh_reality_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0
    }, sort_keys=True))

if __name__ == "__main__":
    main()
