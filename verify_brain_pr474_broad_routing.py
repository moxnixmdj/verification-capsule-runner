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

# Reproduce the exact syntactic class that failed in the spent parent, without executing it.
spent_input=(
    "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater "
    "than the protocol's default initial stream flow-control window. Use authoritative primary "
    "technical evidence and a real executable check. Autonomously discover and verify the relevant "
    "specification, determine how to extract and interpret the required limits, choose and run a "
    "zero-cost verification method, identify material protocol-scope or interpretation limitations, "
    "independently verify the consequential result, and produce a decision-quality answer with provenance."
)
direct=broad.decompose(spent_input)
assert direct["status"]=="DECOMPOSED", direct
routed=grounding.ground(spent_input,{})
assert len(routed["clauses"])>1, routed
assert routed["grounded_clause_count"]==0, routed
assert routed["unresolved_clause_indexes"]==list(range(len(routed["clauses"]))), routed
assert routed["broad_objective_decomposition_available"] is True, routed

# Fresh cross-domain wording must route for the same generic reason.
fresh=(
    "Evaluate whether a thermal coating degrades faster under cyclic heating than steady heating. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Choose and run a zero-cost verification method, identify scope limitations, independently verify "
    "the consequential result, and produce a decision-quality answer."
)
assert broad.decompose(fresh)["status"]=="DECOMPOSED"
fresh_routed=grounding.ground(fresh,{})
assert fresh_routed["broad_objective_decomposition_available"] is True, fresh_routed

# Concrete recipes remain out of the broad-research reinterpretation path.
for explicit in (
    "Assess whether two measured values differ. Run python verify_values.py",
    "Assess whether two measured values differ using https://example.com/data",
    "Assess whether two measured values differ. Execute ./verify_values.sh",
):
    out=broad.decompose(explicit)
    assert out["status"]=="UNSUPPORTED", out
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", out

# Partial grounding must still block whole-goal broad reinterpretation.
registry={
  "measurement.battery.voltage": {
    "status": "VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd": 0,
    "provides": ["measurement.battery.voltage"],
    "requires": [],
    "keywords": ["battery","voltage","measurement"],
    "source": {"type":"python_stdlib"}
  }
}
mixed=(
    "Assess battery voltage measurement behavior. "
    "Investigate unrelated atmospheric circulation evidence."
)
partial=grounding.ground(mixed,registry)
assert partial["grounded_clause_count"]>=1, partial
assert partial["broad_objective_decomposition_available"] is False, partial
assert partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, partial

print("INDEPENDENT_BRAIN_PR474_BROAD_ROUTING_QUALIFICATION_PASS")
