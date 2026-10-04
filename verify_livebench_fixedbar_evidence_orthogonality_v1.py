#!/usr/bin/env python3
import ast, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/"subject/livebench_fixedbar_evidence_orthogonality_v1"
EXPECTED={
 "brain/LIVEBENCH_FIXED_BAR_EVIDENCE_ORTHOGONALITY_V1.json":"1e5f66dc8b8d7500ce96f0be221a88c6f1954093",
 "brain/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "brain/TERMINAL_CLOSURE_MANIFEST_V1.json":"fae1bc5338993911f1078680996aa48e677d7a15",
 "brain/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json":"51e3e7578e9adbeee2168d2223b84481fea16a09",
 "brain/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"2c6bb594d353e4c6a169821da5f84a91be212ca7",
 "brain/LIVEBENCH_SCORE_ONLY_WITNESS_CAPABILITY_QUARANTINE_V1.json":"951586401fb9f4b5c30cd83c78bb6d41cc9cc0d5",
 "upstream/livebench_if_utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
 "upstream/livebench_if_evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
 "upstream/livebench_legacy_evaluation_main.py":"4a341984936c4d609644a3b77f8c030ac5aa7269",
}
def blob(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,h in EXPECTED.items():
 got=blob(BASE/rel); assert got==h,(rel,got,h)

def J(rel): return json.loads((BASE/rel).read_text())
cand=J("brain/LIVEBENCH_FIXED_BAR_EVIDENCE_ORTHOGONALITY_V1.json")
reg=J("brain/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
man=J("brain/TERMINAL_CLOSURE_MANIFEST_V1.json")
beh=J("brain/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json")
rest=J("brain/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
quar=J("brain/LIVEBENCH_SCORE_ONLY_WITNESS_CAPABILITY_QUARANTINE_V1.json")

family="INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT"
ids={"LIVEBENCH_IF_GE_65_7","IF_SCOPE_BOUNDARY_NONINFERIOR","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"}
fps=[x for x in reg["predicates"] if x.get("family")==family]
assert {x["id"] for x in fps}==ids,fps
lb=next(x for x in fps if x["id"]=="LIVEBENCH_IF_GE_65_7")
assert lb["kind"]=="PUBLIC_FIXED_BAR"
assert lb["acceptance"]=="LiveBench Instruction Following >= 65.7%"
assert any("ALL_PREDICATES_FOR_A_FAMILY_MUST_BE_PROVED" in x for x in reg["rules"])

mf=next(x for x in man["families"] if x["id"]==family)
assert mf["closure_state"]=="WHOLE_SCOPE_BEHAVIORAL_PASS__OPUS55_ACCEPTANCE_OPEN"
assert mf["current_behavioral_scope_state"]=="P1_SCOPE_RESTORED__WHOLE_SCOPE_PASS"
assert mf["opus55_acceptance_state"]=="OPEN"

assert beh["family_verdict"]["all_families_pass"] is True
assert family in beh["family_verdict"]["passed_families"]
assert rest["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert rest["verified"]["whole_p1_contract_restored"] is True
assert rest["verified"]["provisional_behavioral_family_pass_count"]==19
assert rest["verified"]["p1_quarantined_behavioral_family_count"]==0

assert quar["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
sched=set(quar["scheduler_effect_if_verified"])
assert "KEEP_THEM_AVAILABLE_FOR_SCORER_ANALYSIS_FORMATTING_OR_OBJECTIVE_THRESHOLD_PROOF_WHERE_ADMISSIBLE" in sched
assert "DO_NOT_COUNT_SCORE_ONLY_STRUCTURAL_OR_TRIGRAM_WITNESS_ROUTES_AS_ROOT1_CAPABILITY_CLOSURE" in sched

utils=(BASE/"upstream/livebench_if_utils.py").read_text()
evalsrc=(BASE/"upstream/livebench_if_evaluation_lib.py").read_text()
legacysrc=(BASE/"upstream/livebench_legacy_evaluation_main.py").read_text()
utree=ast.parse(utils); etree=ast.parse(evalsrc); ltree=ast.parse(legacysrc)
score_node=next(n for n in utree.body if isinstance(n,ast.FunctionDef) and n.name=="score_results")
mod=ast.Module(body=[score_node],type_ignores=[])
ast.fix_missing_locations(mod); ns={}
exec(compile(mod,"score_results","exec"),ns)
score_results=ns["score_results"]
for n in range(1,6):
 for mask in range(1<<n):
  xs=[bool(mask&(1<<i)) for i in range(n)]
  for all_ok in (False,True):
   expected=((1 if all_ok else 0)+sum(xs)/n)/2
   assert score_results(all_ok,xs)==expected

strict_node=next(n for n in etree.body if isinstance(n,ast.FunctionDef) and n.name=="test_instruction_following_strict")
legacy_strict_node=next(n for n in ltree.body if isinstance(n,ast.FunctionDef) and n.name=="test_instruction_following_strict")
calls=[]
for n in ast.walk(strict_node):
 if isinstance(n,ast.Call):
  try: calls.append(ast.unparse(n.func))
  except Exception: pass
assert "instruction.check_following" in calls,calls
strict_text=ast.get_source_segment(evalsrc,strict_node)
for forbidden in ("reference_answer","semantic_quality","model_judge","llm_judge"):
 assert forbidden not in strict_text.lower(),forbidden

legacy_calls=[]
for n in ast.walk(legacy_strict_node):
 if isinstance(n,ast.Call):
  try: legacy_calls.append(ast.unparse(n.func))
  except Exception: pass
assert "instruction.check_following" in legacy_calls,legacy_calls
legacy_strict_text=ast.get_source_segment(legacysrc,legacy_strict_node)
for forbidden in ("reference_answer","semantic_quality","model_judge","llm_judge","ground_truth"):
 assert forbidden not in legacy_strict_text.lower(),forbidden
score_text=ast.get_source_segment(utils,score_node)
for forbidden in ("reference_answer","semantic_quality","model_judge","llm_judge","response"):
 assert forbidden not in score_text.lower(),forbidden

assert cand["theorem"]["false_dependency_deleted"]=="SEMANTIC_SEED_REQUIRED_FOR_EVERY_LIVEBENCH_SCORE_CANDIDATE"
assert cand["theorem"]["no_rule_weakened"] is True
assert cand["scheduler_delta"]["promotion"].endswith("IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS")
for k in ("acceptance_credit_delta","capability_credit_delta","family_credit_delta","ownership_credit_delta"):
 assert cand["accounting"][k]==0
assert cand["execution_authority"] is False
assert cand["promotion_authority"] is False
assert cand["fresh_reality_authority"] is False

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_FIXED_BAR_EVIDENCE_ORTHOGONALITY_PUBLIC_VERIFICATION_V1",
 "status":"PASS",
 "exact_blobs":EXPECTED,
 "verified":{
  "instruction_family_has_exactly_three_acceptance_predicates":True,
  "livebench_is_public_fixed_bar":True,
  "whole_scope_behavioral_pass_is_separately_recorded":True,
  "p1_whole_scope_restoration_independently_passed":True,
  "strict_scorer_is_checker_boolean_only":True,
  "active_legacy_strict_scorer_is_checker_boolean_only":True,
  "score_formula_recomputed_for_all_boolean_patterns_n1_to_n5":True,
  "score_only_helpers_remain_zero_capability_credit":True,
  "family_promotion_still_requires_all_three_predicates":True,
  "semantic_seed_dependency_deleted_only_for_fixed_bar_scoring_evidence":True
 },
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0,
 "capability_credit_delta":0,
 "family_credit_delta":0,
 "ownership_credit_delta":0
}
(ROOT/"livebench_fixedbar_evidence_orthogonality_v1_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
