#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("independent_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

broad=load("broad_objective_decompose")
grounding=load("plain_goal_bound_grounding")

# Exact frozen genomics Task-B language must remain admissible as research-method selection,
# but this qualification does not discover sources, execute tools, or answer the task.
genomics=(
    "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 "
    "is greater than the human mitochondrial reference genome sequence length. Use authoritative "
    "primary technical evidence and a real executable check. Autonomously discover and verify the "
    "relevant primary records, determine how to extract and interpret the two sequence lengths, "
    "choose and run a zero-cost verification method, identify material reference-version or "
    "sequence-scope limitations, independently verify the consequential result, and produce a "
    "decision-quality answer with provenance."
)
g=broad.decompose(genomics)
assert g["status"]=="DECOMPOSED", g
r=grounding.ground(genomics,{})
assert len(r["clauses"])>1, r
assert r["grounded_clause_count"]==0, r
assert r["unresolved_clause_indexes"]==list(range(len(r["clauses"]))), r
assert r["broad_objective_decomposition_available"] is True, r

# Reproduce the independently demonstrated PR474 false negative exactly.
bad=[
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Run customtool --verify values.json",
    "Assess whether two values differ. Run python verify_values.py",
    "Assess whether two values differ. Execute ./verify_values.sh",
    "Assess whether two values differ using https://example.com/data",
    "Assess whether two values differ. Run a verification method with python verify.py",
]
for objective in bad:
    out=broad.decompose(objective)
    assert out["status"]=="UNSUPPORTED", (objective,out)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (objective,out)

# Abstract method-selection language must remain broad across phrasing variants.
good=[
    "Assess whether two values differ. Run a zero-cost verification method, and independently verify the result.",
    "Evaluate whether two regimes differ. Execute a validation procedure, and preserve material limitations.",
    "Investigate whether two observations differ. Run an independently chosen verification approach; preserve provenance.",
]
for objective in good:
    out=broad.decompose(objective)
    assert out["status"]=="DECOMPOSED", (objective,out)

# Partial grounding still forbids whole-goal broad reinterpretation.
registry={
  "measurement.battery.voltage": {
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["measurement.battery.voltage"],
    "requires":[],
    "keywords":["battery","voltage","measurement"],
    "source":{"type":"python_stdlib"}
  }
}
partial=grounding.ground(
    "Assess battery voltage measurement behavior. Investigate unrelated atmospheric circulation evidence.",
    registry,
)
assert partial["grounded_clause_count"]>=1, partial
assert partial["broad_objective_decomposition_available"] is False, partial

print("INDEPENDENT_BRAIN_PR496_EXPLICIT_RECIPE_FAILCLOSED_PASS")
