from __future__ import annotations
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def load(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))
spec=importlib.util.spec_from_file_location("basis_v2",ROOT/"runtime.py")
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)

frontier=load("frontier.json"); overlay=load("overlay.json"); gov=load("governance.json")
out=mod.compile_basis(frontier,overlay)
assert out["status"].startswith("PASS"), out
assert out["global_unresolved_predicate_count"]==31
assert out["global_certificate_count"]==17
assert out["refined_parent_count"]==3
assert out["leaf_requirement_occurrence_count"]==40
assert out["leaf_atom_count"]==40
assert out["exact_duplicate_savings"]==0
assert out["max_structural_target_fanout"]==3
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
assert out["execution_authority"] is False and out["promotion_authority"] is False
assert gov["expected_projection"]["canonical_leaf_atoms"]==40

by={x["proposition"]:x for x in out["atoms"]}
assert by["FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["CODING_FRONTIERCODE_GE_54_4"]
assert by["CURSORBENCH_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["CODING_CURSORBENCH_GE_57_8"]
assert by["PROWORK_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["PROWORK_AA_BRIEFCASE_GE_1822"]
assert by["ARTIFACT_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["ARTIFACT_AA_BRIEFCASE_GE_1822"]

# Adversarial: unverified refinement must fail.
bad=json.loads(json.dumps(overlay)); bad["refinements"][0]["independent_verified"]=False
assert mod.compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"
# Adversarial: target overlap must fail.
bad=json.loads(json.dumps(overlay))
kids=bad["refinements"][1]["children"]
kids[1]["target_predicates"]=kids[0]["target_predicates"]
assert mod.compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"
# Adversarial: exact partition cannot silently change a requirement.
bad=json.loads(json.dumps(overlay))
bad["refinements"][1]["children"][1]["requires"]=["NOT_THE_PARENT_REQUIREMENT"]
assert mod.compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"
# Adversarial: semantic replacement without receipt must fail.
bad=json.loads(json.dumps(overlay)); bad["refinements"][0]["verification_receipt"]=""
assert mod.compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"

print(json.dumps({
 "status":"PASS",
 "projection":{"unresolved":31,"refined_parents":3,"atoms":40,"max_fanout":3},
 "target_associations_verified":4,
 "adversarial_fail_closed_checks":4,
 "credit_delta":0
},indent=2,sort_keys=True))
