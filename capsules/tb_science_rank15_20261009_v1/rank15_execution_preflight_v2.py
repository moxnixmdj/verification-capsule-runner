from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = Path(__file__).resolve().parent
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_PREFLIGHT_V2"
SLOT = "terminal-bench-science/protein-active-learning::trial-0"
DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
WORKFLOW = ".github/workflows/execute-tb-science-rank15-20261009-v2.yml"
BRANCH = "execute/tb-science-rank15-20261009-v2"
BASE = "terminal-execution-v1"
ACTIVATION = "ACTIVATE_RANK15_V2_PR.json"
EXPECTED = {
    "RANK15_PUBLIC_AUTHORITY_BINDING_V2.json": "8ee2719efc69b992b0a73ad751bd3c217be98150",
    "RANK15_PUBLIC_LEDGER_BINDING_V21.json": "62eec1814fa9b1682772f096c36200c0069b9f00",
    "RANK15_EPOCH_V2.json": "cff46526c96069794460c2ba98d0f4e8a33c5440",
    "RANK15_EXECUTION_CLAIM_V2.json": "446d9df3245fa1d40c8bb0912ce957102da2e433",
}
ROOT_EXPECTED = {
    WORKFLOW: "fc3f7fee4b6ff78ed80eb62c9b3e1a1033572561",
    "execution_guard/TB_SCIENCE_RANK15_EXECUTION_BEHAVIOR_V2.json": "5caedddb7b5714fe74c4ba5709a43391e66dcf3a",
    "execution_guard/CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1.json": "3d156b5b3274ea7fe6542206137ddc7c782903b5",
    "execution_guard/terminal_execution_admission_v1.py": "84d1186b012d51fa5faafa37cf52e87467e80857",
    "execution_guard/TB_SCIENCE_RANK15_V2_RUNTIME_SEMANTIC_VERIFICATION_20261009_V1.json": "30b854d096e597a332cf183394a8b67c84a30e53",
    "capsules/tb_science_rank15_20261009_v1/canonical/runtime/harbor_science_planner_v2.py": "92161f95f211377ed40c11a38e641046bb45bd26",
    "capsules/tb_science_rank15_20261009_v1/canonical/runtime/harbor_science_agent_v2.py": "fb4d8202192ca7a7ff03b36b9ba31be48f19dfa4",
    "capsules/tb_science_rank15_20261009_v1/rank15_prestart_token_guard_v2.py": "b296e442535d4cf7770f7c1464da441c80fc65a1",
    "capsules/tb_science_rank15_20261009_v1/canonical/runtime/harbor_environment_transport.py": "ec46f648214a37bb16025d5ef2593efdf59f0d79",
}

def git_blob(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path: Path):
    x=json.loads(path.read_text())
    if not isinstance(x,dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:"+str(path))
    return x

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-activation",action="store_true")
    args=ap.parse_args()
    errors=[]

    for rel,expected in EXPECTED.items():
        p=C/rel
        if not p.is_file():
            errors.append("MISSING:"+rel)
        elif git_blob(p)!=expected:
            errors.append("BLOB_MISMATCH:"+rel)

    for rel,expected in ROOT_EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("MISSING:"+rel)
        elif git_blob(p)!=expected:
            errors.append("BLOB_MISMATCH:"+rel)

    try:
        authority=load(C/"RANK15_PUBLIC_AUTHORITY_BINDING_V2.json")
        ledger=load(C/"RANK15_PUBLIC_LEDGER_BINDING_V21.json")
        epoch=load(C/"RANK15_EPOCH_V2.json")
        claim=load(C/"RANK15_EXECUTION_CLAIM_V2.json")
        surface=load(ROOT/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")

        assert authority["slot_id"]==SLOT and authority["task_digest"]==DIGEST
        assert authority["brain_authority"]["git_blob_sha"]=="a292a898231973204f66bf92c3f70ce2bf422449"
        assert authority["brain_ledger"]["git_blob_sha"]=="475f56128d6e9f22a540db1f007b2dfe47e723f7"
        assert authority["workflow"]["git_blob_sha"]==ROOT_EXPECTED[WORKFLOW]

        assert ledger["consumed_slots"]==14
        assert ledger["next_unconsumed_slot"]["ledger_schedule_rank"]==15
        assert ledger["next_unconsumed_slot"]["slot_id"]==SLOT
        assert ledger["next_unconsumed_slot"]["task_digest"]==DIGEST
        assert ledger["rank15_task_read"] is False and ledger["rank15_task_started"] is False
        assert ledger["rank15_benchmark_trials_consumed"]==0

        assert epoch["slot_id"]==SLOT and epoch["task_digest"]==DIGEST
        assert epoch["execution_branch"]==BRANCH and epoch["execution_base"]==BASE
        assert epoch["public_authority_binding_blob"]==EXPECTED["RANK15_PUBLIC_AUTHORITY_BINDING_V2.json"]
        assert epoch["brain_authority_blob"]=="a292a898231973204f66bf92c3f70ce2bf422449"
        assert epoch["brain_ledger_blob"]=="475f56128d6e9f22a540db1f007b2dfe47e723f7"
        assert epoch["workflow_blob"]==ROOT_EXPECTED[WORKFLOW]
        assert epoch["attempts_authorized"]==1 and epoch["retries_authorized"]==0
        assert epoch["task_read_under_this_epoch"] is False and epoch["task_started"] is False

        assert claim["slot_id"]==SLOT and claim["task_digest"]==DIGEST
        assert claim["execution_branch"]==BRANCH and claim["execution_base"]==BASE
        assert claim["activation_filename"]==ACTIVATION
        assert claim["public_authority_binding_blob"]==EXPECTED["RANK15_PUBLIC_AUTHORITY_BINDING_V2.json"]
        assert claim["brain_authority_blob"]=="a292a898231973204f66bf92c3f70ce2bf422449"
        assert claim["brain_ledger_blob"]=="475f56128d6e9f22a540db1f007b2dfe47e723f7"
        assert claim["epoch_git_blob_sha"]==EXPECTED["RANK15_EPOCH_V2.json"]
        assert claim["workflow_git_blob_sha"]==ROOT_EXPECTED[WORKFLOW]
        assert claim["attempts_authorized"]==1 and claim["retries_authorized"]==0
        assert claim["precheck_failure_consumes_slot"] is False
        assert claim["consumed"] is False and claim["task_started"] is False

        assert surface["workflow_path"]==WORKFLOW
        assert surface["workflow_git_blob_sha"]==ROOT_EXPECTED[WORKFLOW]
        assert surface["slot_id"]==SLOT and surface["task_digest"]==DIGEST
        assert surface["execution_authority"] is True
        assert surface["task_read_authority"] is False
        assert surface["authority"]["git_blob_sha"]==EXPECTED["RANK15_PUBLIC_AUTHORITY_BINDING_V2.json"]
        assert surface["ledger"]["git_blob_sha"]==EXPECTED["RANK15_PUBLIC_LEDGER_BINDING_V21.json"]
        assert surface["epoch"]["git_blob_sha"]==EXPECTED["RANK15_EPOCH_V2.json"]
        assert surface["execution_claim"]["git_blob_sha"]==EXPECTED["RANK15_EXECUTION_CLAIM_V2.json"]
    except Exception as exc:
        errors.append("STRUCTURAL_CHECK:"+type(exc).__name__+":"+str(exc))

    activation_present=(C/ACTIVATION).is_file()
    if args.require_activation:
        try:
            assert activation_present
            arm=load(C/ACTIVATION)
            assert arm["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V2"
            assert arm["activate"] is True
            assert arm["slot_id"]==SLOT and arm["task_digest"]==DIGEST
            assert arm["public_authority_binding_blob"]==EXPECTED["RANK15_PUBLIC_AUTHORITY_BINDING_V2.json"]
            assert arm["epoch_git_blob_sha"]==EXPECTED["RANK15_EPOCH_V2.json"]
            assert arm["execution_claim_git_blob_sha"]==EXPECTED["RANK15_EXECUTION_CLAIM_V2.json"]
            assert arm["attempts_authorized"]==1 and arm["retries_authorized"]==0
            assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
            assert os.environ.get("GITHUB_EVENT_NAME")=="pull_request"
            assert os.environ.get("GITHUB_BASE_REF")==BASE
            assert os.environ.get("GITHUB_HEAD_REF")==BRANCH
        except Exception as exc:
            errors.append("ACTIVATION_CHECK:"+type(exc).__name__+":"+str(exc))
    elif activation_present:
        errors.append("UNEXPECTED_ACTIVATION_FILE_DURING_STAGING")

    out={
        "schema":SCHEMA,
        "status":"PASS__RANK15_V2_EXECUTION_PREFLIGHT__ZERO_TASK_EXPOSURE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "require_activation":args.require_activation,
        "activation_present":activation_present,
        "errors":sorted(set(errors)),
        "task_read":False,
        "task_started":False,
        "benchmark_trials_consumed":0,
        "acceptance_credit_delta":0,
        "terminal_credit_delta":0,
    }
    (ROOT/"RANK15_EXECUTION_PREFLIGHT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
