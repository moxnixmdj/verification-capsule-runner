#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, importlib.util, json, pathlib, shutil, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
OLD_SUBJECT=ROOT/"subject"/"livebench_frozen_runtime_closure_v1"
CURRENT_GC=ROOT/"subject"/"livebench_current_routing_20261005_v1"/"goal_compiler.py"
OLD_VERIFIER=ROOT/"verify_livebench_frozen_runtime_closure_v1.py"
OLD_VERIFIER_BLOB="c91441274d7c37744841bdf2b96262982661f69a"
CURRENT_GC_BLOB="c895df9898bc97e4017f9e42bf6b27357ab1f315"

def git_blob_sha(path: pathlib.Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def old_expected() -> dict[str,str]:
    assert git_blob_sha(OLD_VERIFIER)==OLD_VERIFIER_BLOB, (
        "HISTORICAL_VERIFIER_DRIFT:"+git_blob_sha(OLD_VERIFIER)
    )
    tree=ast.parse(OLD_VERIFIER.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node,ast.Assign):
            if any(isinstance(t,ast.Name) and t.id=="EXPECTED" for t in node.targets):
                obj=ast.literal_eval(node.value)
                assert isinstance(obj,dict) and len(obj)==21
                return {str(k):str(v) for k,v in obj.items()}
    raise AssertionError("HISTORICAL_EXPECTED_MAP_NOT_FOUND")

historical=old_expected()
for rel,want in historical.items():
    path=OLD_SUBJECT/rel
    assert path.is_file(), "HISTORICAL_SUBJECT_MISSING:"+rel
    got=git_blob_sha(path)
    assert got==want, f"HISTORICAL_SUBJECT_DRIFT:{rel}:{want}:{got}"

assert CURRENT_GC.is_file()
assert git_blob_sha(CURRENT_GC)==CURRENT_GC_BLOB, (
    "CURRENT_GOAL_COMPILER_BLOB_MISMATCH:"+git_blob_sha(CURRENT_GC)
)

with tempfile.TemporaryDirectory(prefix="livebench-current-routing-") as td:
    subject=pathlib.Path(td)/"subject"
    shutil.copytree(OLD_SUBJECT,subject)
    gc_path=subject/"canonical"/"runtime"/"goal_compiler.py"
    gc_path.write_bytes(CURRENT_GC.read_bytes())

    current=dict(historical)
    current["canonical/runtime/goal_compiler.py"]=CURRENT_GC_BLOB
    for rel,want in current.items():
        got=git_blob_sha(subject/rel)
        assert got==want, f"COMPOSED_SUBJECT_BLOB_MISMATCH:{rel}:{want}:{got}"

    spec=importlib.util.spec_from_file_location("livebench_current_goal_compiler",gc_path)
    assert spec is not None and spec.loader is not None
    compiler=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=compiler
    spec.loader.exec_module(compiler)

    # Generalization checks are deliberately outside the LiveBench sentinel.
    general=compiler.compile_goal("Reply with exactly GENERAL_ROUTE_OK.",{},subject)
    assert general["compiler_mode"]=="DETERMINISTIC_EXACT_LITERAL_RESPONSE", general
    assert general["finish_summary"]=="GENERAL_ROUTE_OK", general
    assert general["controller_actions"]==[
        {"type":"finish","args":{"summary":"GENERAL_ROUTE_OK"}}
    ], general
    assert general["clause_coverage_verified"] is True, general

    multi=compiler.compile_goal('Respond with exactly "alpha beta!".',{},subject)
    assert multi["finish_summary"]=="alpha beta!", multi

    ambiguous_rejected=False
    try:
        compiler.compile_goal(
            "Reply with exactly GENERAL_ROUTE_OK and create output.json.",
            {},
            subject,
        )
    except compiler.GoalCompilationFailure:
        ambiguous_rejected=True
    assert ambiguous_rejected, "AMBIGUOUS_LITERAL_TAIL_WAS_NOT_REJECTED"

    probe=r'''
import json, pathlib, sys
subject=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(subject))
sys.path.insert(0,str(subject/"canonical"/"runtime"))
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter
request={
 "benchmark_id":"LIVEBENCH_IF_2026_06_25",
 "task_id":"SYNTHETIC_ZERO_CASE_INFERENCE",
 "allowed_tools":[],
 "task_payload":{"instruction":"Reply with exactly SYNTHETIC_OK."},
}
out=adapter.infer(request)
print("SYNTHETIC_RESULT="+json.dumps(out,sort_keys=True))
'''
    p=subprocess.run(
        [sys.executable,"-c",probe,str(subject)],
        text=True,capture_output=True,timeout=45,
    )
    assert p.returncode==0, (
        "SYNTHETIC_ZERO_CASE_NONPASS\nSTDOUT:\n"+p.stdout[-8000:]
        +"\nSTDERR:\n"+p.stderr[-12000:]
    )
    line=next(
        (x for x in p.stdout.splitlines() if x.startswith("SYNTHETIC_RESULT=")),
        None,
    )
    assert line is not None, "SYNTHETIC_RESULT_MISSING"
    result=json.loads(line.split("=",1)[1])
    assert result["status"]=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE", result
    assert result["answer"]=="SYNTHETIC_OK", result
    assert result["cognition_dependency_class"]=="MODEL_INDEPENDENT", result
    assert result["model_dependency_count"]==0, result

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_CURRENT_GENERAL_ROUTING_VERIFICATION_20261005_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__GENERAL_EXACT_LITERAL_ROUTE__SAME_SYNTHETIC_ZERO_CASE_PASS__ZERO_CREDIT",
 "historical_package_verifier_blob":OLD_VERIFIER_BLOB,
 "historical_package_file_count":len(historical),
 "current_goal_compiler_blob":CURRENT_GC_BLOB,
 "generalization":{
   "different_unquoted_literal_pass":True,
   "quoted_multiword_literal_pass":True,
   "ambiguous_tail_fail_closed":True,
 },
 "same_synthetic_zero_case":{
   "instruction":"Reply with exactly SYNTHETIC_OK.",
   "status":result["status"],
   "answer":result["answer"],
   "cognition_dependency_class":result["cognition_dependency_class"],
   "model_dependency_count":result["model_dependency_count"],
 },
 "consequence":"DELETE_GENERAL_INSTRUCTION_ROUTING_OR_CAPABILITY_SELECTION_AS_CURRENT_LIVEBENCH_ZERO_CASE_BLOCKER__ADVANCE_TO_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_REBIND_VERIFICATION",
 "terminal_case_content_read":False,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0,
 "external_frontier_model_calls":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
}
print("LIVEBENCH_CURRENT_ROUTING_RECEIPT="+json.dumps(receipt,sort_keys=True))
print("PASS: current generic exact-literal instruction routing closes the preexposed LiveBench synthetic zero-case blocker")
