#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
REPORT=ROOT/"pr496_explicit_recipe_qualification.json"

def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+rel)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def require(cond,label,detail=None):
    if not cond:
        raise AssertionError(label+(":"+repr(detail) if detail is not None else ""))

def main():
    authored=subprocess.run(
        [sys.executable,"canonical/tests/test_broad_objective_semantic_decomposition.py"],
        cwd=ROOT,text=True,capture_output=True
    )
    require(authored.returncode==0,"AUTHORED_REGRESSION_FAILED",authored.stdout[-3000:]+authored.stderr[-3000:])
    d=load("canonical/runtime/bound_capabilities/broad_objective_decompose.py","pr496_broad")
    g=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","pr496_ground")

    allowed=[
      "Assess whether two measured values differ. Execute a validation procedure, and independently verify the result.",
      "Evaluate whether two regimes differ. Run an independently chosen verification approach; preserve material limitations.",
      "Investigate whether the two measurements disagree. Run a zero-cost verification method, identify scope limitations, and preserve provenance.",
      "Quantify whether the observed values differ. Execute a free checking strategy and independently verify the consequential result.",
      "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 is greater than the human mitochondrial reference genome sequence length. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify the relevant primary records, determine how to extract and interpret the two sequence lengths, choose and run a zero-cost verification method, identify material reference-version or sequence-scope limitations, independently verify the consequential result, and produce a decision-quality answer with provenance."
    ]
    denied=[
      "Assess whether two values differ. Run /usr/bin/python verify_values.py",
      "Assess whether two values differ. Execute /opt/tools/custom --check values.json",
      "Assess whether two values differ. Run customtool --verify values.json",
      "Assess whether two values differ. Execute customtool",
      "Assess whether two values differ. Run ./verify",
      "Assess whether two values differ. Run verify.py",
      "Assess whether two values differ. Run python",
      "Assess whether two values differ. Run a verification method with python verify.py",
      "Assess whether two values differ. Run a zero-cost verification method using customtool --check",
      "Assess whether two values differ using https://example.com/data and extract JSON path value",
      "Assess whether two values differ. Save result.json after checking."
    ]
    report={"schema":"BRAIN_PR496_EXPLICIT_RECIPE_BOUNDARY_QUALIFICATION_V1","allowed":[],"denied":[],"model_dependency_count":0,"incremental_spend_usd":0,"parent_task_execution":False}
    for s in allowed:
        out=d.decompose(s)
        require(out.get("status")=="DECOMPOSED","LEGITIMATE_BROAD_OBJECTIVE_REJECTED",(s,out))
        report["allowed"].append({"objective":s,"status":"PASS"})
    for s in denied:
        out=d.decompose(s)
        require(out.get("status")=="UNSUPPORTED","EXPLICIT_RECIPE_ADMITTED",(s,out))
        require(out.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE","WRONG_REJECT_REASON",(s,out))
        report["denied"].append({"objective":s,"status":"PASS"})

    genomics=allowed[-1]
    grounded=g.ground(genomics,{})
    require(grounded.get("grounded_clause_count")==0,"GENOMICS_GROUNDING_UNEXPECTED",grounded)
    require(grounded.get("broad_objective_decomposition_available") is True,"GENOMICS_BROAD_ROUTE_NOT_AVAILABLE",grounded)
    require((grounded.get("broad_objective_decomposition") or {}).get("status")=="DECOMPOSED","GENOMICS_BROAD_ROUTE_NOT_DECOMPOSED",grounded)
    require(grounded.get("model_dependency_count")==0,"MODEL_DEPENDENCY",grounded)

    partial_registry={"python.tests.audit.unittest":{"status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,"provides":["python.tests.audit"],"requires":[],"keywords":["python","tests","audit","unittest","passed","failed","skipped"]}}
    partial=g.ground("Assess whether an unknown material property changed between regimes. Audit the Python tests with unittest and report failed counts.",partial_registry)
    require(partial.get("grounded_clause_count",0)>=1,"PARTIAL_GROUNDING_EXPECTED",partial)
    require(partial.get("broad_objective_decomposition_available") is False,"PARTIAL_GROUNDING_HIJACK",partial)

    report["authored_regressions"]="PASS"
    report["genomics_nonexecuting_route"]="PASS"
    report["partial_grounding_control"]="PASS"
    report["status"]="PASS"
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("INDEPENDENT_PR496_EXPLICIT_RECIPE_BOUNDARY_PASS")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
