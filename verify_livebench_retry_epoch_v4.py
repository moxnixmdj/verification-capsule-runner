#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXEC=ROOT/"execute_livebench_replay72_v4.py"
CAND=ROOT/"subject/livebench_retry_v4_20261004/LIVEBENCH_RETRY_EXECUTION_EPOCH_V4_CANDIDATE.json"
TRUTH=ROOT/"subject/livebench_retry_v4_20261004/LIVEBENCH_SECOND_DIRECT_ATTEMPT_TRUTH_RECEIPT_20261004_V1.json"
EXPECTED_CAND_BLOB="2b9dcdc466ae3519a4378011394d1f4145840638"
EXPECTED_TRUTH_BLOB="e5e1aa48046c2f6a95413a0a9f804e36a5cf2f9e"
POLICY_BLOCK="POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION"

def git_blob_sha(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main()->int:
    assert git_blob_sha(CAND)==EXPECTED_CAND_BLOB
    assert git_blob_sha(TRUTH)==EXPECTED_TRUTH_BLOB
    cand=json.loads(CAND.read_text())
    truth=json.loads(TRUTH.read_text())
    assert cand["retry_scope"]["first_required_replay"]=="EXACT_ALREADY_ATTEMPTED_72_CASE_PREFIX_ONLY"
    assert cand["retry_scope"]["new_case_exposure_before_replay_validation"] is False
    assert "NO_POST_PROMPT_CAPABILITY_ACQUISITION" in cand["forbidden_repairs"]
    assert truth["causal_invalidity_for_capability_judgment"]["predicate_failure_admissible"] is False
    assert truth["causal_invalidity_for_capability_judgment"]["root1_reopen_authorized"] is False
    assert truth["execution"]["terminal_result"]["terminal_cases_consumed"]==72

    source=EXEC.read_text()
    assert "REPLAY_LIMIT = 72" in source
    assert "for start in range(0,REPLAY_LIMIT,BATCH):" in source
    assert "for start in range(0,POPULATION,BATCH):" not in source
    assert "_load_auto_capability_acquisition = _blocked_auto_acquisition" in source
    assert "POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION" in source
    assert 'new_case_exposure_authorized":False' in source
    assert 'TemporaryDirectory(prefix="lb-case-")' in source
    assert "shutil.copytree(template, case / \"root\", dirs_exist_ok=True)" in source

    spec=importlib.util.spec_from_file_location("replay",EXEC)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert mod.FROZEN_RUNTIME_CLOSURE_FILE_COUNT==24
    for _,(rel,expected) in mod.RUNTIME_FILES.items():
        p=ROOT/rel
        assert p.is_file(), rel
        assert git_blob_sha(p)==expected,(rel,git_blob_sha(p),expected)
    for src_rel,(_,expected) in mod.RUNTIME_CLOSURE_EXTRA.items():
        p=ROOT/src_rel
        assert p.is_file(),src_rel
        assert git_blob_sha(p)==expected,(src_rel,git_blob_sha(p),expected)

    import tempfile
    with tempfile.TemporaryDirectory(prefix="verify-lb-retry-v4-") as td:
        template=mod.build_runtime_template(pathlib.Path(td))
        q1={"question_id":"ZERO_CASE_BOUND_CAPABILITY_SMOKE","turns":["Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json."]}
        _,answer,err=mod.infer_one(template,q1)
        assert err is None,err
        assert answer
        q2={"question_id":"ZERO_CASE_POLICY_BLOCK_SMOKE","turns":["Respond with exactly SYNTHETIC_OK."]}
        _,answer2,err2=mod.infer_one(template,q2)
        assert answer2==""
        assert err2==POLICY_BLOCK,(err2,)
        assert not [p for p in (template/"canonical/astra_runtime/state").rglob("*") if p.is_file()]
        assert not [p for p in (template/"canonical/astra_runtime/evidence").rglob("*") if p.is_file()]

    print(json.dumps({
      "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
      "executor_git_blob_sha":git_blob_sha(EXEC),
      "retry_candidate_git_blob_sha":EXPECTED_CAND_BLOB,
      "second_attempt_truth_git_blob_sha":EXPECTED_TRUTH_BLOB,
      "frozen_runtime_closure_file_count":24,
      "replay_case_count":72,
      "per_case_filesystem_isolation_verified":True,
      "post_prompt_acquisition_guard_verified":True,
      "second_attempt_not_capability_evidence_verified":True,
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "new_case_exposure_authorized":False,
      "global_fresh_reality_authority":False,
      "acceptance_credit_delta":0
    },sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
