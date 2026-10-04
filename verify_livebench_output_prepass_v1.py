#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
INPUT=ROOT/"subject/livebench_output_prepass_v1/INPUT.json"
RUNTIME=ROOT/"subject/root2_output_threshold_dag_v1/canonical/runtime/threshold_proof_dag_v1.py"
EXPECTED_RUNTIME_BLOB="7a0c715d931dbba05bc9e5ae344e1ead787ea5b8"

def blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main()->int:
    errors=[]
    if blob(RUNTIME)!=EXPECTED_RUNTIME_BLOB:
        errors.append("THRESHOLD_RUNTIME_BLOB_MISMATCH")
    spec=importlib.util.spec_from_file_location("threshold_dag",RUNTIME)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    doc=json.loads(INPUT.read_text())
    out=mod.compile_threshold_proof_dag(doc)
    comp=out.get("compiled") or {}
    checks={
      "status":out.get("status")=="PASS",
      "target":out.get("target_id")=="LIVEBENCH_IF_GE_65_7",
      "metric":out.get("metric_kind")=="ADDITIVE_THRESHOLD",
      "verdict":comp.get("verdict")=="OPEN",
      "lower":comp.get("lower")=="0",
      "upper":comp.get("upper")=="200",
      "threshold":comp.get("threshold")=="131.4",
      "pass_deficit":comp.get("pass_deficit")=="131.4",
      "minimum_pass_cut":comp.get("minimum_pass_cut") is None,
      "minimum_fail_cut":comp.get("minimum_fail_cut") is None,
      "no_blocked_actions":out.get("blocked_fresh_reality_actions")==[],
      "no_authority":out.get("execution_authority") is False and out.get("fresh_reality_authority") is False and out.get("promotion_authority") is False,
    }
    for k,v in checks.items():
        if not v: errors.append("CHECK_FAILED:"+k)
    result={
      "schema":"PROJECT_BRAIN_LIVEBENCH_OUTPUT_ONLY_THRESHOLD_PREPASS_PUBLIC_VERIFIER_V1",
      "status":"PASS__OPEN__ZERO_REALITY_CANNOT_FORCE_THRESHOLD__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "target_predicate":"LIVEBENCH_IF_GE_65_7",
      "runtime_git_blob_sha":EXPECTED_RUNTIME_BLOB,
      "input_sha256":hashlib.sha256(INPUT.read_bytes()).hexdigest(),
      "compiled":comp,
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "candidate_inferences":0,
      "fresh_reality_authority":False,
      "execution_authority":False,
      "promotion_authority":False,
      "acceptance_credit_delta":0,
      "incremental_spend_usd":0,
      "errors":errors,
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
