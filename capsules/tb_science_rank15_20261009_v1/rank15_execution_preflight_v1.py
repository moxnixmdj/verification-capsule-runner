from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

C = Path(__file__).resolve().parent
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_PREFLIGHT_V1"
SLOT = "terminal-bench-science/protein-active-learning::trial-0"
DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
EXPECTED = {
    "TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json":"61629b854f4be1e940a3f68d1a676e40b4e61ebf",
    "ACTION_INTENT_TB_SCIENCE_RANK15_20261009_V1.json":"ce2c7aeb17c450e17b02a3b616ce8a8374edabe4",
    "TB_SCIENCE_RANK15_AUTHORITY_CANDIDATE_PUBLIC_VERIFICATION_20261009_V1.json":"75f2ca9b52e256e13551977e99784dca868c11a7",
    "TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_CANDIDATE_20261009_V1.json":"88ffb2b0117a9fb7f8885118171b53b187bc581d",
    "TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261009_V19.json":"c9b887ac4fb57046be666492748d25ca96056378",
    "TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json":"6dfa880b1f68881531afbba6ca211681801fd19b",
    "TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261009_V12.json":"8008b1e2382c1235e3b788e0f8d4ab9a48487409",
    "TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_V12_VERIFICATION_20261009_V1.json":"2f604985baa7f88c61b23958d59dc2ecd4c0990b",
    "FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json":"b20c5cd6965f7ea7e5ca019d1e828ac6eced042c",
    "RANK15_EPOCH_V1.json":"063761501704d31db73428200bc559f9eb2b038a",
    "RANK15_EXECUTION_CLAIM_V1.json":"5818601880d54efd856e5a27b9cb14e9b6021e7e",
    "rank15_prestart_token_guard_v1.py":"6956c6dd1f7b6e6a964bc927876d96aa479de476",
    "canonical/runtime/harbor_science_agent_v1.py":"e7e258f567499bd7356c0276d6293aa30dbd338c",
    "canonical/runtime/harbor_science_planner_v1.py":"58964dc8d6b5eed5c202081cd800035c791eeb1d",
    "canonical/runtime/harbor_command_policy.py":"a525773417291c7a4841bf35e1baff5370350d0d",
}

def git_blob(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name: str):
    return json.loads((C/name).read_text())

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-activation", action="store_true")
    args=ap.parse_args()
    errors=[]
    for rel, expected in EXPECTED.items():
        p=C/rel
        if not p.is_file():
            errors.append("MISSING:"+rel); continue
        actual=git_blob(p)
        if actual!=expected:
            errors.append(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")

    try:
        a=load("TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json")
        l=load("TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261009_V19.json")
        e=load("RANK15_EPOCH_V1.json")
        claim=load("RANK15_EXECUTION_CLAIM_V1.json")
        cm=load("TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261009_V12.json")
        assert a["execution_authority"] is True and a["task_read_authority"] is False
        assert a["slot"]["id"]==SLOT and a["slot"]["digest"]==DIGEST and a["slot"]["ledger_schedule_rank"]==15
        assert a["state"]["task_started"] is False and a["state"]["authority_consumed"] is False
        assert a["state"]["benchmark_trials_consumed"]==0
        assert a["controls"]["attempts_authorized"]==1 and a["controls"]["retries_authorized"]==0
        assert a["controls"]["precheck_failure_consumes_slot"] is False
        assert a["controls"]["frozen_requirements_after_first_cycle"] is True
        assert a["controls"]["later_substrate_requirement_redeclaration_authority"] is False
        assert a["controls"]["candidate_covers_outside_frozen_set_fail_closed"] is True
        assert l["current_counts"]["consumed_slots"]==14
        n=l["current_counts"]["next_unconsumed_slot"]
        assert n["ledger_schedule_rank"]==15 and n["slot_id"]==SLOT and n["task_digest"]==DIGEST
        assert l["rank15"]["task_started"] is False
        assert l["rank15"]["execution_authority_consumed"] is False
        assert l["rank15"]["benchmark_trials_consumed"]==0
        assert e["authority_blob"]==EXPECTED["TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json"]
        assert e["run_attempts_authorized_by_epoch"]==0 and e["task_started"] is False
        assert claim["execution_branch"]=="execute-tb-science-rank15-v1-20261009"
        assert claim["authority_git_blob_sha"]==EXPECTED["TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json"]
        assert claim["epoch_git_blob_sha"]==EXPECTED["RANK15_EPOCH_V1.json"]
        assert claim["consumed"] is False and claim["task_started"] is False
        assert claim["retries_authorized"]==0 and claim["precheck_failure_consumes_slot"] is False
        assert claim["frozen_requirements_after_first_cycle"] is True
        assert claim["later_substrate_requirement_redeclaration_authority"] is False
        assert claim["candidate_covers_outside_frozen_set_fail_closed"] is True
        assert cm["closure_file_count"]==15 and len(cm["closure"])==15 and cm["unresolved_dynamic_imports"]==[]
        for row in cm["closure"]:
            p=C/row["path"]
            assert p.is_file()
            assert git_blob(p)==row["git_blob_sha"]
    except Exception as exc:
        errors.append("STRUCTURAL_CHECK:"+type(exc).__name__+":"+str(exc))

    activation_present=(C/"ACTIVATE_RANK15_PR.json").is_file()
    if args.require_activation:
        try:
            assert activation_present
            arm=load("ACTIVATE_RANK15_PR.json")
            assert arm["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V1"
            assert arm["activate"] is True
            assert arm["slot_id"]==SLOT and arm["task_digest"]==DIGEST
            assert arm["authority_git_blob_sha"]==EXPECTED["TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json"]
            assert arm["epoch_git_blob_sha"]==EXPECTED["RANK15_EPOCH_V1.json"]
            assert arm["execution_claim_git_blob_sha"]==EXPECTED["RANK15_EXECUTION_CLAIM_V1.json"]
            assert arm["attempts_authorized"]==1 and arm["retries_authorized"]==0
            assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
            assert os.environ.get("GITHUB_EVENT_NAME")=="pull_request"
            assert os.environ.get("GITHUB_BASE_REF")=="terminal-execution-v1"
            assert os.environ.get("GITHUB_HEAD_REF")=="execute-tb-science-rank15-v1-20261009"
        except Exception as exc:
            errors.append("ACTIVATION_CHECK:"+type(exc).__name__+":"+str(exc))
    elif activation_present:
        errors.append("UNEXPECTED_ACTIVATION_FILE_DURING_STAGING")

    out={
        "schema":SCHEMA,
        "status":"PASS__RANK15_EXECUTION_PREFLIGHT__ZERO_TASK_EXPOSURE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "require_activation":args.require_activation,
        "activation_present":activation_present,
        "errors":errors,
        "task_read":False,
        "task_started":False,
        "benchmark_trials_consumed":0,
        "acceptance_credit_delta":0,
        "terminal_credit_delta":0,
    }
    Path("RANK15_EXECUTION_PREFLIGHT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
