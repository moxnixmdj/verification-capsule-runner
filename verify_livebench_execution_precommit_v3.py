#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, os, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/"subject/livebench_execution_precommit_v3"
MANIFEST=BASE/"canonical/governance/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V3.json"
RUNTIME=BASE/"canonical/runtime/livebench_if_execution_precommit_v3.py"
TESTS=BASE/"canonical/tests/test_livebench_if_execution_precommit_v3.py"
RECEIPT=BASE/"legacy_scorer_verification.json"
EXPECTED={
 "manifest":"11912e787bed100e509b4a21cadb072935c68218",
 "runtime":"75a81861569b008c8708d6e4d5b8c3a6a6f61285",
 "tests":"81352316ede7d77129be6035b7a8f521eb416585",
 "receipt":"8282b4fe307020fef13ac6421262c18ce7f8c0e8",
}
def blob(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def main():
    if os.environ.get("GITHUB_ACTIONS")!="true":
        raise SystemExit("FAIL:GITHUB_ACTIONS_REQUIRED")
    if sys.version_info[:2]!=(3,12):
        raise SystemExit("FAIL:PYTHON_3_12_REQUIRED")
    for k,p in (("manifest",MANIFEST),("runtime",RUNTIME),("tests",TESTS),("receipt",RECEIPT)):
        got=blob(p)
        if got!=EXPECTED[k]:
            raise SystemExit(f"FAIL:SUBJECT_BLOB_DRIFT:{k}:{got}:{EXPECTED[k]}")
    spec=importlib.util.spec_from_file_location("lbv3",RUNTIME)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    m=json.loads(MANIFEST.read_text())
    out=mod.verify_precommit(m)
    if out.get("precommit_pass") is not True:
        raise SystemExit("FAIL:V3_PRECOMMIT:"+json.dumps(out,sort_keys=True))
    if out.get("execution_authority") is not False or out.get("fresh_reality_authority") is not False:
        raise SystemExit("FAIL:V3_SELF_AUTHORIZED")
    if out.get("legacy_environment_preflight_proved") is not False:
        raise SystemExit("FAIL:V3_MANIFEST_SELF_PROVES_ENVIRONMENT")

    # Independent negative mutation checks, not merely trusting the subject tests.
    x=copy.deepcopy(m); x["candidate"]["commit"]="0"*40
    if mod.verify_precommit(x)["precommit_pass"] is not False: raise SystemExit("FAIL:CANDIDATE_MUTATION_NOT_REJECTED")
    x=copy.deepcopy(m); x["scorer"]["dispatch_cutoff"]="2025-11-26"
    if mod.verify_precommit(x)["precommit_pass"] is not False: raise SystemExit("FAIL:DISPATCH_MUTATION_NOT_REJECTED")
    x=copy.deepcopy(m); x["scorer"]["verifier_files"]=[r for r in x["scorer"]["verifier_files"] if r[0]!="livebench/if_runner/instruction_following_eval/evaluation_main.py"]
    if mod.verify_precommit(x)["precommit_pass"] is not False: raise SystemExit("FAIL:LEGACY_SCORER_REMOVAL_NOT_REJECTED")
    x=copy.deepcopy(m); x["environment"]["packages"]=[r for r in x["environment"]["packages"] if r[0]!="langdetect"]
    if mod.verify_precommit(x)["precommit_pass"] is not False: raise SystemExit("FAIL:LEGACY_DEP_REMOVAL_NOT_REJECTED")
    for field in ("repair_design_terminal_prompt_content_used","repair_design_candidate_response_used","repair_design_score_used"):
        x=copy.deepcopy(m); x["case_exposure"][field]=True
        if mod.verify_precommit(x)["precommit_pass"] is not False: raise SystemExit("FAIL:CONTAMINATION_NOT_REJECTED:"+field)

    rec=json.loads(RECEIPT.read_text())
    if rec.get("status")!="INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_PUBLIC_LEGACY_AND_CURRENT_SCORERS__ZERO_TERMINAL_CASES__ZERO_CREDIT":
        raise SystemExit("FAIL:SCORER_RECEIPT_STATUS")
    v=rec.get("verified") or {}
    required={
      "exact_dispatch_rule_source_pass":True,
      "legacy_ifeval_strict_synthetic_pass":True,
      "current_ifbench_strict_synthetic_pass":True,
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "candidate_inferences":0,
      "candidate_mutation":False,
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0,
    }
    for k,val in required.items():
        if v.get(k)!=val: raise SystemExit("FAIL:SCORER_RECEIPT_FIELD:"+k)
    if (rec.get("subject") or {}).get("git_blob_sha")!="13105f751550ea89646bb82bd4c1d8325afe2840":
        raise SystemExit("FAIL:SCORER_SUBJECT_IDENTITY")

    print(json.dumps({
      "schema":"PROJECT_BRAIN_LIVEBENCH_EXECUTION_PRECOMMIT_V3_PUBLIC_VERIFIER_RESULT_V1",
      "status":"PASS",
      "subject_blobs":EXPECTED,
      "v3_component_digests_recomputed":True,
      "candidate_unchanged":True,
      "dispatch_cutoff":"2025-11-25",
      "legacy_plus_ifbench_closure_bound":True,
      "scorer_environment_independent_receipt_bound":True,
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "candidate_inferences":0,
      "incremental_spend_usd":0,
      "execution_authority":False,
      "fresh_reality_authority":False,
      "promotion_authority":False,
      "acceptance_credit_delta":0
    },sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
