from __future__ import annotations
import json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"verification"))
from requirement_graph_kernel import compile_requirement_contract, requirement_mutation_score
from independent_acceptance_model import assess

contract=json.loads((Path(__file__).with_name("wdm_design_stage_b_contract_v2.json")).read_text())
reqs=contract["normalized_requirements"]
checks=contract["independent_acceptance_plan"]["checks"]
expected=[r["id"] for r in reqs]

graph=compile_requirement_contract(reqs, expected_required_ids=expected)
mut=requirement_mutation_score(reqs)
acceptance=assess({"requirements":reqs,"checks":checks})

assert graph["pass"], graph
assert mut["pass"], mut
assert acceptance["pass"], acceptance
assert len(reqs)==15
assert contract["source"]["instruction_blob_sha"]=="ab7255e9b4cf9597e965e2fe385447e502c4e8f9"
assert contract["behavioral_contract"]["polarization"]["meep_eig_parity"]=="mp.ODD_Z"
assert contract["behavioral_contract"]["performance"][0]["wavelengths_um"]==[1.50,1.51,1.52,1.53,1.54]
assert contract["behavioral_contract"]["performance"][1]["wavelengths_um"]==[1.56,1.57,1.58,1.59,1.60]
assert contract["behavioral_contract"]["performance"][0]["mean_transmission_gte"]==0.87
assert contract["behavioral_contract"]["performance"][1]["mean_transmission_gte"]==0.87
assert contract["behavioral_contract"]["performance"][0]["other_output_leakage_lte"]==0.15
assert contract["behavioral_contract"]["performance"][1]["other_output_leakage_lte"]==0.15
assert contract["behavioral_contract"]["binary_pattern"]["binary_fraction_required"]==1.0
assert contract["behavioral_contract"]["drc"]["each_component_max_inscribed_diameter_um_gte"]==0.12
assert contract["behavioral_contract"]["design_bounds"]["output_edge_gap_um_gte"]==0.30
assert contract["task_execution_authorized"] is False

# Falsification checks: delete a requirement and remove one acceptance detector.
bad=json.loads(json.dumps(contract))
bad["normalized_requirements"]=bad["normalized_requirements"][1:]
bad_graph=compile_requirement_contract(bad["normalized_requirements"], expected_required_ids=expected)
assert not bad_graph["pass"]

bad2=json.loads(json.dumps(contract))
target=bad2["independent_acceptance_plan"]["checks"][0]
target["detects"]=[]
bad_accept=assess({"requirements":bad2["normalized_requirements"],"checks":bad2["independent_acceptance_plan"]["checks"]})
assert not bad_accept["pass"]

print(json.dumps({
  "schema":"RANK15_STAGE_B_INDEPENDENT_STRUCTURAL_VERIFICATION_V1",
  "pass":True,
  "requirement_count":len(reqs),
  "requirement_mutants":mut["total"],
  "requirement_mutants_survived":mut["survived"],
  "acceptance_failed_requirements":acceptance["failed_requirements"],
  "negative_requirement_omission_killed":True,
  "negative_acceptance_coverage_loss_killed":True,
  "task_execution_performed":False
},indent=2))
