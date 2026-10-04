#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
CANDIDATE_PATH=ROOT/"subject/livebench_second_epoch_retry_v1/CANDIDATE.json"
ACTIVATION_PATH=ROOT/"subject/livebench_second_epoch_retry_v1/ACTIVATION.json"
EXPECTED_CANDIDATE_BLOB="929277c01d2772eb13f5f5d8264a4f869dd018b2"
EXPECTED_ACTIVATION_BLOB="6450468944242e9e0d03cd06873e395f065b031e"
REPO="moxnixmdj/verification-capsule-runner"
FAILED_HEAD="d8e6edd61fb1fbeedd856aa31cc202348e52529c"
FAILED_DRIVER_BLOB="05d71d3d06ebac9b5d74eb31b137141e6b8797c2"
CORRECTED_HEAD="9a88ff65f80d7e8604083c0543eb918d188e477c"
CORRECTED_DRIVER_BLOB="e9db4e7553397035aed67186f0065e4a79fa7732"
FAILED_RUN=37188253705
FAILED_JOB=111394777574
SCORER_RUN=37188804615
SCORER_SUBJECT_BLOB="13105f751550ea89646bb82bd4c1d8325afe2840"

def blob_sha_bytes(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def blob_sha(path:pathlib.Path)->str:
    return blob_sha_bytes(path.read_bytes())

def get(url:str, *, accept:str="application/vnd.github+json")->bytes:
    headers={"Accept":accept,"User-Agent":"project-brain-independent-verifier"}
    tok=os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"]="Bearer "+tok
        headers["X-GitHub-Api-Version"]="2022-11-28"
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def get_json(url:str):
    return json.loads(get(url).decode())

def raw(ref:str,path:str)->bytes:
    return get(f"https://raw.githubusercontent.com/{REPO}/{ref}/{path}",accept="text/plain")

def main()->int:
    errors=[]
    if blob_sha(CANDIDATE_PATH)!=EXPECTED_CANDIDATE_BLOB:
        errors.append("CANDIDATE_BLOB_MISMATCH")
    if blob_sha(ACTIVATION_PATH)!=EXPECTED_ACTIVATION_BLOB:
        errors.append("ACTIVATION_BLOB_MISMATCH")
    cand=json.loads(CANDIDATE_PATH.read_text())
    act=json.loads(ACTIVATION_PATH.read_text())

    # Public GitHub run truth for the failed first attempt.
    run=get_json(f"https://api.github.com/repos/{REPO}/actions/runs/{FAILED_RUN}")
    if run.get("conclusion")!="failure" or run.get("head_sha")!=FAILED_HEAD:
        errors.append("FAILED_RUN_IDENTITY_OR_CONCLUSION_MISMATCH")
    jobs=get_json(f"https://api.github.com/repos/{REPO}/actions/runs/{FAILED_RUN}/jobs?per_page=100")
    job=next((x for x in jobs.get("jobs",[]) if int(x.get("id",0))==FAILED_JOB),None)
    if not job or job.get("conclusion")!="failure":
        errors.append("FAILED_JOB_IDENTITY_OR_CONCLUSION_MISMATCH")
    try:
        logs=get(f"https://api.github.com/repos/{REPO}/actions/jobs/{FAILED_JOB}/logs",accept="application/octet-stream").decode("utf-8","replace")
    except Exception as exc:
        errors.append("FAILED_LOG_FETCH:"+type(exc).__name__)
        logs=""
    if "FAIL_CLOSED:UNKNOWN_INSTRUCTION_IDS:" not in logs:
        errors.append("EXPECTED_PREINFERENCE_FAILURE_SENTINEL_MISSING")
    if "LIVEBENCH_CASE_RECEIPT=" in logs or "LIVEBENCH_TERMINAL_RESULT=" in logs:
        errors.append("CANDIDATE_RESULT_OUTPUT_OBSERVED_IN_FAILED_RUN")

    failed_driver=raw(FAILED_HEAD,"execute_livebench_if_threshold_v1.py")
    if blob_sha_bytes(failed_driver)!=FAILED_DRIVER_BLOB:
        errors.append("FAILED_DRIVER_BLOB_MISMATCH")
    fs=failed_driver.decode()
    i_unknown=fs.find('if unknown:')
    i_raise=fs.find('raise SystemExit("FAIL_CLOSED:UNKNOWN_INSTRUCTION_IDS:',i_unknown)
    i_template=fs.find("template=build_runtime_template(base)")
    i_infer=fs.find("raw=list(ex.map(lambda q: infer_one(template,q),batch))")
    if not (0<=i_unknown<i_raise<i_template<i_infer):
        errors.append("FAILED_DRIVER_PREINFERENCE_ORDER_NOT_PROVED")

    # Independently verified scorer-only repair.
    sr=get_json(f"https://api.github.com/repos/{REPO}/actions/runs/{SCORER_RUN}")
    if sr.get("conclusion")!="success":
        errors.append("SCORER_VERIFICATION_RUN_NOT_SUCCESS")
    scorer_subject=raw("f0d7d8eb3381043f93e11028221b1f983d620f7c",
        "subject/livebench_legacy_scorer_supplement_v1/LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_V1.json")
    if blob_sha_bytes(scorer_subject)!=SCORER_SUBJECT_BLOB:
        errors.append("SCORER_SUPPLEMENT_SUBJECT_BLOB_MISMATCH")
    sj=json.loads(scorer_subject)
    if sj.get("derivation_independence",{}).get("terminal_prompt_content_used_to_design_repair") is not False:
        errors.append("SCORER_REPAIR_TERMINAL_PROMPT_INDEPENDENCE_NOT_PROVED")
    if sj.get("derivation_independence",{}).get("candidate_response_used_to_design_repair") is not False:
        errors.append("SCORER_REPAIR_RESPONSE_INDEPENDENCE_NOT_PROVED")
    if sj.get("derivation_independence",{}).get("score_used_to_design_repair") is not False:
        errors.append("SCORER_REPAIR_SCORE_INDEPENDENCE_NOT_PROVED")

    # Exact corrected driver must preserve candidate/population/threshold/order and only add proper dispatch.
    corrected=raw(CORRECTED_HEAD,"execute_livebench_if_threshold_v1.py")
    if blob_sha_bytes(corrected)!=CORRECTED_DRIVER_BLOB:
        errors.append("CORRECTED_DRIVER_BLOB_MISMATCH")
    cs=corrected.decode()
    required=[
      'POPULATION = 200',
      'THRESHOLD = 0.657',
      'DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"',
      'DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"',
      '"astra_runtime": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py", "7f5d16b1db69cb620954bc778e0ba6e15e687b75")',
      'str(q.get("livebench_release_date") or "") < "2025-11-25"',
      'case_score(ifbench_eval,legacy_eval,q,answer)',
      '"case_order":"QUESTION_ID_ASCENDING_FIXED_PREEXECUTION"',
      '"adaptive_case_selection":False',
      '"case_replacement":False',
      '"immutabledict==4.3.1"',
      '"pandas==2.3.3"',
      '"livebench/gen_ground_truth_judgment.py": "b36561da5b54380c724c507462d0ee65feefeac8"',
    ]
    for token in required:
        if token not in cs:
            errors.append("CORRECTED_DRIVER_REQUIRED_TOKEN_MISSING:"+hashlib.sha256(token.encode()).hexdigest()[:12])

    # Candidate/activation may authorize exactly one predicate-local retry epoch, never promotion/global reality.
    if cand.get("execution_authority") is not False or cand.get("fresh_reality_authority") is not False:
        errors.append("CANDIDATE_PREMATURE_AUTHORITY")
    auth=act.get("authority") or {}
    if auth.get("authorized_predicates")!=["LIVEBENCH_IF_GE_65_7"]:
        errors.append("ACTIVATION_SCOPE_WIDENED")
    if auth.get("execution_epochs_authorized")!=1 or auth.get("candidate_execution_epochs_authorized")!=1:
        errors.append("ACTIVATION_NOT_ONE_EPOCH")
    if auth.get("global_fresh_reality") is not False or auth.get("promotion") is not False or auth.get("acceptance_credit") is not False:
        errors.append("ACTIVATION_GRANTS_FORBIDDEN_AUTHORITY")
    if act.get("exact_execution_binding",{}).get("corrected_driver_git_blob_sha")!=CORRECTED_DRIVER_BLOB:
        errors.append("ACTIVATION_DRIVER_BINDING_MISMATCH")

    passed=not errors
    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_SECOND_EPOCH_RETRY_AUTHORITY_INDEPENDENT_VERDICT_V1",
      "status":"PASS__PREVIOUS_EXPOSURE_PREINFERENCE__SCORER_ONLY_REPAIR__ONE_EXACT_RETRY_EPOCH_ELIGIBLE__ZERO_CREDIT" if passed else "FAIL_CLOSED",
      "independent_public_runner_pass":passed,
      "retry_epoch_eligible":passed,
      "failed_attempt_pre_candidate_inference":passed and "FAIL_CLOSED:UNKNOWN_INSTRUCTION_IDS:" in logs,
      "scorer_repair_independent_zero_case_pass":passed and sr.get("conclusion")=="success",
      "corrected_driver_exact_binding_pass":passed and blob_sha_bytes(corrected)==CORRECTED_DRIVER_BLOB,
      "candidate_blob_sha":EXPECTED_CANDIDATE_BLOB,
      "activation_blob_sha":EXPECTED_ACTIVATION_BLOB,
      "prior_population_exposure_preserved":True,
      "authorized_predicates":["LIVEBENCH_IF_GE_65_7"] if passed else [],
      "execution_epochs_authorized":1 if passed else 0,
      "global_fresh_reality_authority":False,
      "promotion_authority":False,
      "acceptance_credit_delta":0,
      "incremental_spend_usd":0,
      "errors":errors,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())
