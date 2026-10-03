#!/usr/bin/env python3
from __future__ import annotations
import copy, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PTR=ROOT/"subjects/adaptive_terminal_closure_active_pointer_v1.json"
REC=ROOT/"subjects/adaptive_terminal_closure_controller_verification_v1.json"

EXPECTED_PTR_BLOB="99a48da27f73461d4be999e834ac7709322f8686"
EXPECTED_REC_BLOB="4fd30df49b44d76cf508dca06ba386336a4f1481"
EXPECTED_ACTIVATION="78dda53305200ed466099db8658840980b2126fc"
EXPECTED_RUNTIME="06d16ef1e8caa08835bc4e958c3047833bf52a32"
EXPECTED_TESTS="874706e94596cde028bed872cc40f07f6fa0d843"
EXPECTED_V10="54be838a5a0a9698398893ad113641496d5051b8"
EXPECTED_RUN=37121349377
EXPECTED_JOB=111197924322

def blob(path:Path)->str:
    rel=path.relative_to(ROOT).as_posix()
    return subprocess.check_output(["git","rev-parse",f"HEAD:{rel}"],text=True).strip()

def load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def errors(p,r):
    e=[]
    if p.get("schema")!="PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_ACTIVE_AUTHORITY_V1": e.append("POINTER_SCHEMA")
    if not str(p.get("status","")).startswith("CANDIDATE_ACTIVE_POINTER__"): e.append("POINTER_STATUS")
    b=p.get("base_scheduling_authority") or {}
    if b.get("git_blob_sha")!=EXPECTED_V10: e.append("V10_HASH")
    if b.get("rule")!="V10_REMAINS_UNMODIFIED_AND_AUTHORITATIVE_FOR_EXECUTION_GATING": e.append("V10_RULE")
    c=p.get("adaptive_controller") or {}
    if c.get("activation_git_blob_sha")!=EXPECTED_ACTIVATION: e.append("ACTIVATION_HASH")
    if c.get("runtime_git_blob_sha")!=EXPECTED_RUNTIME: e.append("RUNTIME_HASH")
    if c.get("tests_git_blob_sha")!=EXPECTED_TESTS: e.append("TESTS_HASH")
    iv=p.get("independent_verification") or {}
    if iv.get("path")!="canonical/verification/ADAPTIVE_TERMINAL_CLOSURE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": e.append("RECEIPT_PATH")
    if iv.get("external_repository")!="moxnixmdj/verification-capsule-runner": e.append("VERIFIER_REPO")
    if iv.get("external_pull_request")!=1326: e.append("VERIFIER_PR")
    if iv.get("workflow_run_id")!=EXPECTED_RUN: e.append("VERIFIER_RUN")
    if iv.get("workflow_job_id")!=EXPECTED_JOB: e.append("VERIFIER_JOB")
    if iv.get("conclusion")!="success": e.append("VERIFIER_CONCLUSION")
    pol=p.get("live_policy") or {}
    if pol.get("tool_discovery_retrieval")!="MANDATORY_V3_OVER_VERIFIED_V2_BASE": e.append("TOOL_DISCOVERY_GATE")
    if pol.get("probabilities_schedule_only") is not True: e.append("PROBABILITY_AUTHORITY")
    if pol.get("unknown_probabilities")!="UNKNOWN_NOT_INVENTED": e.append("UNKNOWN_PROBABILITY")
    for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
        if p.get(k) is not False: e.append("POINTER_"+k.upper())
    for k in ("capability_credit_delta","family_credit_delta","ownership_credit_delta","incremental_spend_usd"):
        if p.get(k)!=0: e.append("POINTER_"+k.upper())

    if r.get("schema")!="PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_PUBLIC_RUNNER_VERIFICATION_20261003_V1": e.append("RECEIPT_SCHEMA")
    if not str(r.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"): e.append("RECEIPT_STATUS")
    s=r.get("subject") or {}
    if s.get("activation_git_blob_sha")!=EXPECTED_ACTIVATION: e.append("R_ACTIVATION_HASH")
    if s.get("runtime_git_blob_sha")!=EXPECTED_RUNTIME: e.append("R_RUNTIME_HASH")
    if s.get("tests_git_blob_sha")!=EXPECTED_TESTS: e.append("R_TESTS_HASH")
    if s.get("current_v10_authority_git_blob_sha")!=EXPECTED_V10: e.append("R_V10_HASH")
    pub=r.get("public_runner") or {}
    if pub.get("pull_request")!=1326: e.append("R_PR")
    if pub.get("workflow_run_id")!=EXPECTED_RUN: e.append("R_RUN")
    if pub.get("workflow_job_id")!=EXPECTED_JOB: e.append("R_JOB")
    if pub.get("conclusion")!="success": e.append("R_CONCLUSION")
    claims=r.get("verified_claims") or {}
    if claims.get("current_live_world")!="11_OF_38_PROVED__27_OPEN__4_OF_19_ACCEPTANCE": e.append("LIVE_WORLD")
    if claims.get("primitive_work_units")!=33: e.append("WORK_UNITS")
    if claims.get("matched_priority_child_facts")!=16: e.append("MATCHED_FACTS")
    if claims.get("ownership_reconciliation_units")!=2: e.append("OWNERSHIP_UNITS")
    if claims.get("tool_discovery_v3_gate_required") is not True: e.append("V3_GATE")
    if claims.get("authority_leakage") is not False: e.append("AUTHORITY_LEAKAGE")
    for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
        if r.get(k) is not False: e.append("RECEIPT_"+k.upper())
    for k in ("capability_credit_delta","family_credit_delta","ownership_credit_delta","incremental_spend_usd"):
        if r.get(k)!=0: e.append("RECEIPT_"+k.upper())
    return sorted(set(e))

def main():
    assert blob(PTR)==EXPECTED_PTR_BLOB,(blob(PTR),EXPECTED_PTR_BLOB)
    assert blob(REC)==EXPECTED_REC_BLOB,(blob(REC),EXPECTED_REC_BLOB)
    p,r=load(PTR),load(REC)
    base=errors(p,r)
    assert base==[],base

    mutations=[]
    cases=[
      ("EXECUTION_AUTHORITY", lambda q: q.__setitem__("execution_authority",True)),
      ("V10_HASH", lambda q: q["base_scheduling_authority"].__setitem__("git_blob_sha","0"*40)),
      ("TOOL_GATE", lambda q: q["live_policy"].__setitem__("tool_discovery_retrieval","BYPASS")),
      ("RECEIPT_RUN", lambda q: q["independent_verification"].__setitem__("workflow_run_id",0)),
    ]
    for name,mut in cases:
        q=copy.deepcopy(p); mut(q)
        assert errors(q,r),name
        mutations.append(name)
    rr=copy.deepcopy(r); rr["public_runner"]["conclusion"]="failure"
    assert errors(p,rr),"RECEIPT_CONCLUSION_MUTATION"
    mutations.append("RECEIPT_CONCLUSION")

    out={
      "schema":"PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_ACTIVE_POINTER_PUBLIC_RUNNER_VERIFICATION_V1",
      "status":"PASS",
      "pointer_blob":EXPECTED_PTR_BLOB,
      "controller_receipt_blob":EXPECTED_REC_BLOB,
      "v10_blob":EXPECTED_V10,
      "activation_blob":EXPECTED_ACTIVATION,
      "runtime_blob":EXPECTED_RUNTIME,
      "tests_blob":EXPECTED_TESTS,
      "workflow_run_id":EXPECTED_RUN,
      "workflow_job_id":EXPECTED_JOB,
      "mutation_cases_killed":mutations,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "ownership_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":
    main()
