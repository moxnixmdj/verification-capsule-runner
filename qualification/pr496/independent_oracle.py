#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
spec=importlib.util.spec_from_file_location("pr496_independent_decomposer",P)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def expect(obj,status):
    out=mod.decompose(obj)
    assert out["status"]==status,(obj,out)
    return out

# Fresh adversarial concrete recipes: every executable operand must fail closed.
for obj in [
    "Assess whether two values differ. Run /opt/custom/bin/python verify_values.py",
    "Compare two observations. Execute customtool --input values.json",
    "Evaluate whether two regimes differ. Run C:\\Tools\\verify.exe --check",
    "Determine whether two quantities differ. Run ./unknownbinary --verify",
    "Assess whether two values differ. Run a verification method with python verify.py",
    "Compare two values. Execute a validation approach using https://example.invalid/data",
    "Evaluate a relation. Run an analysis method; then execute mysterycli --check",
]:
    out=expect(obj,"UNSUPPORTED")
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",out

# Abstract method-selection wording must remain admissible broad research.
for obj in [
    "Assess whether two measured values differ. Run a zero-cost verification method, and independently verify the result.",
    "Evaluate whether two regimes differ. Execute an independently selected validation approach; preserve material limitations.",
    "Determine whether a technical limit differs across regimes. Run an autonomously chosen analysis procedure and preserve provenance.",
    "Compare two documented quantities. Execute a free checking strategy, and independently verify the consequential result.",
]:
    out=expect(obj,"DECOMPOSED")
    assert out["model_dependency_count"]==0,out
    assert out["role_count"]==5,out

# Non-research commands still fail closed.
expect("Run /usr/bin/python verify.py","UNSUPPORTED")
expect("Create output.json with one record","UNSUPPORTED")

report={
 "schema":"PROJECT_BRAIN_PR496_INDEPENDENT_ADVERSARIAL_QUALIFICATION_V1",
 "status":"PASS",
 "source_brain_pr":496,
 "source_brain_head":"d472da3082c8a26d16b91aad0997cb369ee5180e",
 "parent_task_execution":False,
 "parent_task_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr496-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("INDEPENDENT_PR496_EXPLICIT_RECIPE_FAILCLOSED_PASS")
print(json.dumps(report,sort_keys=True))
