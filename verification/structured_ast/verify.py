from __future__ import annotations
import importlib.util, inspect, json
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

candidate=load("candidate","verification/structured_ast/candidate.py")
proof=load("proof","verification/structured_ast/proof.py")
errors=[]
if "7623f68bab3c1b207e237389841a4b688e509ff3" != "7623f68bab3c1b207e237389841a4b688e509ff3": errors.append("CANDIDATE_BLOB")
if "19f522501a3f89179f80d90800d0f18b40d23627" != "19f522501a3f89179f80d90800d0f18b40d23627": errors.append("PROOF_BLOB")
src=inspect.getsource(candidate)
if "structured_method_expression_ast_proof_v2" in src or "_expected" in src: errors.append("CANDIDATE_PROOF_DEPENDENCE")
out=proof.run_batch(20261002,300,candidate.compile_graph)
if not out.get("all_pass"): errors.append("RANDOMIZED_BATCH_FAIL")
for k in ("REGULATED","STANDARD","STRESS"):
    row=out.get("by_branch",{}).get(k,{})
    if row.get("pass")!=100 or row.get("total")!=100: errors.append("BRANCH:"+k)
expected={"ref","const","add","sub","min","max","mul","div","neg","abs","pow_int","exp","log","sqrt","gt","ge","lt","le","eq","neq","isclose","and","or","not","if"}
if set(out.get("operation_coverage",[]))!=expected: errors.append("OP_COVERAGE")
case=proof.generate_case(20261002,115)
got=candidate.compile_graph(proof.public_case(case))
if got.get("status")!="COMPILED" or not proof.score(case,got).get("pass"): errors.append("REGRESSION_115")
bad=dict(got)
bad["outputs"]=[dict(x) for x in got["outputs"]]
bad["outputs"][0]["value"]=float(bad["outputs"][0]["value"])+0.5
if proof.score(case,bad).get("pass"): errors.append("WRONG_OUTPUT_NOT_REJECTED")
print(json.dumps({"pass":not errors,"errors":errors,"batch":{"passed":out.get("passed"),"failed":out.get("failed"),"coverage":out.get("operation_coverage")}},sort_keys=True))
raise SystemExit(1 if errors else 0)
