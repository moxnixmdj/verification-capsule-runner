#!/usr/bin/env python3
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
path=ROOT/"broad_objective_decompose.py"
spec=importlib.util.spec_from_file_location("orthogonal_broad_decomposer",path)
if spec is None or spec.loader is None:
    raise RuntimeError("MODULE_LOAD_FAILED")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

objective=(
    "Evaluate whether Alloy Alpha fatigue life is greater than Alloy Beta fatigue life. "
    "Use authoritative primary materials evidence, choose and run a zero-cost verification "
    "method, identify scope limitations, and independently verify the consequential result."
)
out=mod.decompose(objective)
assert out.get("status")=="DECOMPOSED", out
assert [r.get("role") for r in out.get("roles",[])]==[
    "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION",
], out

concrete=mod.decompose(
    "Evaluate whether Alloy Alpha fatigue life is greater than Alloy Beta fatigue life. "
    "Run python verify_fatigue.py"
)
assert concrete.get("status")=="UNSUPPORTED", concrete
assert concrete.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", concrete

print("ORTHOGONAL_GENERIC_RUN_LANGUAGE_ACCEPTED_AND_CONCRETE_COMMAND_REJECTED")
print("objective_domain=MATERIALS_FATIGUE")
