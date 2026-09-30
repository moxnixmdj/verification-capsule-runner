#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={"producer":"48fd058430d8d361fc75beced567c7b6d1166531","tests":"467a9f4f9b835ca8f65fd19b9335770e7b0ef31b","relation":"d66a7eb30774f66160b698d8082947776888293d"}
FILES={"producer":ROOT/"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py","tests":ROOT/"canonical/tests/test_objective_claim_operand_binding.py","relation":ROOT/"canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py"}
def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
observed={k:git_blob(v) for k,v in FILES.items()}
if observed!=EXPECTED: raise SystemExit("EXACT_BLOB_MISMATCH:"+json.dumps(observed,sort_keys=True))
subprocess.run([sys.executable,"canonical/tests/test_objective_claim_operand_binding.py"],cwd=ROOT,check=True)
subprocess.run([sys.executable,"guarded_claim_spec_fresh_qualification_b.py"],cwd=ROOT,check=True)
report=json.loads((ROOT/"guarded-claim-spec-fresh-qualification-b-report.json").read_text(encoding="utf-8"))
if report.get("status")!="PASS": raise SystemExit("FRESH_QUALIFICATION_B_NOT_PASS")
summary={"schema":"PROJECT_BRAIN_GUARDED_CLAIM_SPEC_FRESH_QUALIFICATION_B_RESULT_V1","status":"PASS","brain_canonical_base":"84b7779f66e1f37970cb8df1cbac0b8d09037a34","exact_blobs":observed,"fresh_corpus":"B","parent_task_execution":False,"parent_task_replay":False,"model_dependency_count":0,"incremental_spend_usd":0}
(ROOT/"guarded-claim-spec-fresh-qualification-b-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(summary,sort_keys=True))
