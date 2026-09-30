#!/usr/bin/env python3
import importlib.util, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"
def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr474_"+name,p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
broad=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

objectives=[
 "Assess whether a ceramic's thermal diffusivity is greater in one phase than another. Use authoritative primary technical evidence. Choose and run a zero-cost verification method, state scope limitations, and independently verify the result.",
 "Determine whether a stellar cluster is older than another population. Use authoritative primary technical evidence and a real executable check. Choose and run a zero-cost verification method and independently verify the result.",
 "Evaluate whether database commit latency is greater under one isolation regime than another. Use authoritative primary technical evidence. Choose and run a zero-cost verification method and preserve provenance.",
]
for objective in objectives:
    direct=broad.decompose(objective)
    assert direct["status"]=="DECOMPOSED", direct
    out=ground.ground(objective,{})
    assert len(out["clauses"])>1, out
    assert out["grounded_clause_count"]==0, out
    assert out["unresolved_clause_indexes"]==list(range(len(out["clauses"]))), out
    assert out["broad_objective_decomposition_available"] is True, out

for explicit in [
 "Assess whether two values differ. Run python verify_values.py",
 "Determine whether values differ using https://example.com/data",
 "Evaluate whether values differ. Save result.json with the answer.",
]:
    x=broad.decompose(explicit)
    assert x["status"]=="UNSUPPORTED", x
    assert x["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", x

registry={
 "battery.voltage.measurement":{
   "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
   "provides":["battery voltage measurement"],"requires":[],
   "keywords":["battery","voltage","measurement"],"result_fields":[]
 }
}
mixed="Assess battery voltage measurement behavior. Investigate unrelated atmospheric circulation evidence."
x=ground.ground(mixed,registry)
assert x["grounded_clause_count"]>=1, x
assert x["broad_objective_decomposition_available"] is False, x
assert x["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, x

rt=(ROOT/"qualification/pr474/astra_runtime_currentbase.py").read_text(encoding="utf-8")
i_broad=rt.find('broad=grounding.get("broad_objective_decomposition")')
i_front=rt.find("_run_open_research_source_frontend",i_broad)
i_auto=rt.find("_load_auto_capability_acquisition()",i_broad)
assert -1 not in (i_broad,i_front,i_auto), (i_broad,i_front,i_auto)
assert i_broad < i_front < i_auto, (i_broad,i_front,i_auto)
print("PR474_EXACT_GUARDED_INDEPENDENT_QUALIFICATION_PASS")
