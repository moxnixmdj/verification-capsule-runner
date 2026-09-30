#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, hashlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
DEC=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
REPORT=ROOT/"qualification/pr496/pr496-independent-report.json"
EXPECTED_DEC="3ded762075ed222228a14877af631f1e2e6d9e4c"
EXPECTED_GROUND="46e8e7466479ea298c34e5fa682d49c374510ce9"
EXPECTED_TEST="4717bd5ebf4b4e6521abf331e93e9675c1b8a785"

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

assert blob(DEC)==EXPECTED_DEC,(blob(DEC),EXPECTED_DEC)
assert blob(ROOT/"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py")==EXPECTED_GROUND
assert blob(ROOT/"canonical/tests/test_broad_objective_semantic_decomposition.py")==EXPECTED_TEST

spec=importlib.util.spec_from_file_location("pr496_dec",DEC)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
checks=[]
def expect(name,text,status,reason=None):
    out=mod.decompose(text)
    assert out["status"]==status,(name,out)
    if reason is not None:
        assert out.get("reason")==reason,(name,out)
    checks.append({"name":name,"status":"PASS","observed":out["status"]})

R="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"
expect("known_absolute_path","Assess whether two values differ. Run /usr/bin/python verify_values.py","UNSUPPORTED",R)
expect("unknown_cli","Assess whether two values differ. Run customtool --verify values.json","UNSUPPORTED",R)
expect("absolute_unknown_executable","Evaluate whether two outputs differ. Execute /opt/local/checker --fast","UNSUPPORTED",R)
expect("generic_phrase_with_concrete_tool","Assess whether two values differ. Run a verification method with python verify.py","UNSUPPORTED",R)
expect("generic_phrase_colon_concrete_command","Assess whether two values differ. Run a verification method: /usr/bin/python verify_values.py","UNSUPPORTED",R)
expect("generic_phrase_colon_unknown_cli","Assess whether two values differ. Run a validation approach: customtool --verify values.json","UNSUPPORTED",R)

genomics=("Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 is greater than the human mitochondrial reference genome sequence length. "
"Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify the relevant primary records, determine how to extract and interpret the two sequence lengths, "
"choose and run a zero-cost verification method, identify material reference-version or sequence-scope limitations, independently verify the consequential result, and produce a decision-quality answer with provenance.")
expect("fresh_genomics_goal_remains_broad",genomics,"DECOMPOSED")
expect("abstract_execute_validation_procedure","Evaluate whether two regimes differ. Execute a validation procedure, and independently verify the result.","DECOMPOSED")
expect("abstract_run_selected_approach","Evaluate whether two regimes differ. Run an independently chosen verification approach; preserve material limitations.","DECOMPOSED")

report={"schema":"PROJECT_BRAIN_PR496_INDEPENDENT_ADVERSARIAL_QUALIFICATION_V1","status":"PASS","brain_pr":496,"brain_head":"d472da3082c8a26d16b91aad0997cb369ee5180e",
"exact_blobs":{"decomposer":EXPECTED_DEC,"grounding":EXPECTED_GROUND,"authored_tests":EXPECTED_TEST},"checks":checks,
"parent_task_execution_count":0,"model_dependency_count":0,"incremental_spend_usd":0}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
