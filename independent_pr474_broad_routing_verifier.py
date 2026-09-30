#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent

def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+rel)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def check(cond,label,detail=None):
    if not cond:
        raise AssertionError(label + (((":")+repr(detail)) if detail is not None else ""))

proc=subprocess.run(
    [sys.executable,"canonical/tests/test_broad_objective_semantic_decomposition.py"],
    cwd=ROOT,text=True,capture_output=True
)
check(proc.returncode==0,"AUTHORED_REGRESSION_FAILED",proc.stdout[-3000:]+proc.stderr[-3000:])

d=load("canonical/runtime/bound_capabilities/broad_objective_decompose.py","pr496_broad")
g=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","pr496_grounding")

generic_ok=[
    "Assess whether two measured values differ. Execute a validation procedure, and independently verify the result.",
    "Evaluate whether two regimes differ. Run an independently chosen verification approach; preserve material limitations.",
    "Determine whether a rate changed. Run a zero-cost verification method, and independently verify the result.",
    "Compare two reported values. Execute an autonomous checking strategy; preserve uncertainty.",
]
for i,goal in enumerate(generic_ok):
    out=d.decompose(goal)
    check(out["status"]=="DECOMPOSED",f"GENERIC_METHOD_{i}_WRONGLY_REJECTED",out)

explicit=[
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Run /opt/custom/tool --verify values.json",
    "Assess whether two values differ. Run customtool --verify values.json",
    "Assess whether two values differ. Execute ./verify_values.py",
    "Assess whether two values differ. Execute mysterycli --check",
    "Assess whether two values differ. Run python verify_values.py",
    "Assess whether two values differ. Run a verification method with python verify.py",
    "Assess whether two values differ using https://example.com/data",
]
for i,goal in enumerate(explicit):
    out=d.decompose(goal)
    check(out["status"]=="UNSUPPORTED",f"EXPLICIT_RECIPE_{i}_WAS_ADMITTED",out)
    check(out.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",
          f"EXPLICIT_RECIPE_{i}_WRONG_REASON",out)

fresh=(
    "Assess whether material conductivity differs between two operating regimes. "
    "Use authoritative primary evidence and a real executable check. "
    "Autonomously discover and verify relevant sources, choose and run a zero-cost "
    "verification method, identify material limitations, independently verify the result, "
    "and produce a decision-quality answer."
)
direct=d.decompose(fresh)
check(direct["status"]=="DECOMPOSED","FRESH_BROAD_OBJECTIVE_REJECTED",direct)
out=g.ground(fresh,{})
check(out["broad_objective_decomposition_available"] is True,"BROAD_ROUTE_NOT_EXPOSED",out)
check(out["grounded_clause_count"]==0,"UNEXPECTED_GROUNDING",out)
check(out["model_dependency_count"]==0,"MODEL_DEPENDENCY",out)

receipt={
    "schema":"PR496_EXPLICIT_RECIPE_FAILCLOSED_V2_INDEPENDENT_QUALIFICATION_V1",
    "status":"PASS",
    "brain_pr":496,
    "candidate_broad_blob":"3ded762075ed222228a14877af631f1e2e6d9e4c",
    "candidate_test_blob":"4717bd5ebf4b4e6521abf331e93e9675c1b8a785",
    "red_run_reproduced_class":"ABSOLUTE_PATH_AND_UNKNOWN_CLI_EXPLICIT_RECIPES",
    "generic_method_positive_cases":len(generic_ok),
    "explicit_recipe_negative_cases":len(explicit),
    "broad_route_preserved":True,
    "parent_task_execution":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
}
(ROOT/"pr496_explicit_recipe_failclosed_v2_qualification.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print("PR496_EXPLICIT_RECIPE_FAILCLOSED_V2_INDEPENDENT_PASS")
print(json.dumps(receipt,sort_keys=True))
