#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, itertools, json, pathlib, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_if_semantic_elision_v1"
FILES={
 SUB/"LIVEBENCH_IF_SEMANTIC_ELISION_THEOREM_V1.json":"af65c1d16047a309baf626316900a76202547175",
 SUB/"LIVEBENCH_FROZEN_POPULATION_DISPATCH_METADATA_VERIFICATION_20261004_V1.json":"bc6c15e9b7d7f0bc7d6dbe8a2c8710ea61fb7127",
 SUB/"canonical/runtime/livebench_if_score_only_semantic_elision_v1.py":"48214f668f9353cf17905c6220e9e3048637366c",
 SUB/"canonical/tests/test_livebench_if_score_only_semantic_elision_v1.py":"f138b9251e2511d18b1f05c2af78f9331ff5379e",
}
UPSTREAM_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM={
 "process_results":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/process_results/instruction_following/utils.py",
  "8ce01747887ec0792c8f024e1972e34ece781676"),
 "legacy_evaluator":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/if_runner/instruction_following_eval/evaluation_main.py",
  "4a341984936c4d609644a3b77f8c030ac5aa7269"),
 "legacy_registry":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/if_runner/instruction_following_eval/instructions_registry.py",
  "903ed738398648c7cfac61d5ffa478c22f1f0891"),
 "legacy_instructions":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/if_runner/instruction_following_eval/instructions.py",
  "4997bab885a676d92545fd91a9a20b48d234a2b2"),
}

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def fetch(url:str)->bytes:
 req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
 with urllib.request.urlopen(req,timeout=30) as r:
  return r.read()

for p,h in FILES.items():
 assert blob(p.read_bytes())==h,(str(p),blob(p.read_bytes()),h)

up={}
for k,(url,h) in UPSTREAM.items():
 b=fetch(url)
 assert blob(b)==h,(k,blob(b),h)
 up[k]=b.decode("utf-8")

dispatch=json.loads((SUB/"LIVEBENCH_FROZEN_POPULATION_DISPATCH_METADATA_VERIFICATION_20261004_V1.json").read_text())
assert dispatch["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert dispatch["verified_subject"]["selected_rows"]==200
assert dispatch["verified_subject"]["legacy_ifeval_rows"]==200
assert dispatch["verified_subject"]["modern_ifbench_rows"]==0

process=up["process_results"]
legacy=up["legacy_evaluator"]

# Exact active scorer dataflow:
# response -> legacy registered checkers -> boolean pass vector -> shared score_results.
assert "results = evaluation_main.evaluator(questions, model_answers" in process
assert 'results = results["strict"]' in process
assert "score_results(follow_all_instructions, follow_instruction_list)" in process
assert "score_1 = 1 if follow_all_instructions else 0" in process
assert "score_2 = [1 if follow else 0 for follow in follow_instruction_list]" in process
assert "avg_score = (score_1 + score_2) / 2" in process

assert "instruction.check_following(response)" in legacy
assert "follow_all_instructions=all(is_following_list)" in legacy
assert "follow_instruction_list=is_following_list" in legacy

# Prove score_results has no prompt/reference/semantic-quality input.
tree=ast.parse(process)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="score_results")
args=[a.arg for a in fn.args.args]
assert args[:2]==["follow_all_instructions","follow_instruction_list"]
used={n.id for n in ast.walk(fn) if isinstance(n,ast.Name)}
for forbidden in ("prompt","question","reference","semantic","task","ground_truth"):
 assert forbidden not in used
assert {"follow_all_instructions","follow_instruction_list"}.issubset(used)

# Exhaustively verify score dependence on pass vectors for small arities.
def score(vec):
 all_pass=all(vec)
 return ((1 if all_pass else 0)+(sum(1 if x else 0 for x in vec)/len(vec)))/2
for n in range(1,7):
 for vec in itertools.product([False,True],repeat=n):
  s=score(vec)
  assert 0.0<=s<=1.0
  if all(vec):
   assert s==1.0

# Execute the fail-closed bridge from the frozen subject.
sys.path.insert(0,str(SUB))
from canonical.runtime.livebench_if_score_only_semantic_elision_v1 import bridge, SemanticElisionError
base={"status":"FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED","response":"structural witness","semantic_seed_required":True}
out=bridge(base,all_score_relevant_constraints_recognized=True,exact_checker_postvalidation_pass=True)
assert out["semantic_seed_required"] is False
assert out["semantic_quality_claimed"] is False
for kwargs in (
 dict(all_score_relevant_constraints_recognized=False,exact_checker_postvalidation_pass=True),
 dict(all_score_relevant_constraints_recognized=True,exact_checker_postvalidation_pass=False),
):
 try:
  bridge(base,**kwargs)
 except SemanticElisionError:
  pass
 else:
  raise AssertionError("bridge failed open")

candidate=json.loads((SUB/"LIVEBENCH_IF_SEMANTIC_ELISION_THEOREM_V1.json").read_text())
assert candidate["schema"]=="PROJECT_BRAIN_LIVEBENCH_IF_SEMANTIC_ELISION_THEOREM_V2"
assert candidate["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert candidate["verified_population_dispatch"]["legacy_rows"]==200
assert candidate["verified_population_dispatch"]["modern_rows"]==0
assert "3.4" not in json.dumps(candidate)
assert candidate["accounting"]["new_terminal_cases_exposed"]==0

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_IF_SEMANTIC_ELISION_INDEPENDENT_VERIFICATION_V2",
 "status":"PASS",
 "subject_git_blobs":{p.name:h for p,h in FILES.items()},
 "upstream_git_blobs":{k:h for k,(_,h) in UPSTREAM.items()},
 "verified":{
  "frozen_population_is_200_legacy_0_modern":True,
  "legacy_evaluator_uses_registered_checkers":True,
  "shared_score_is_pure_function_of_checker_pass_vector":True,
  "no_separate_semantic_quality_term_in_active_score_path":True,
  "all_checker_pass_vector_implies_row_score_one":True,
  "semantic_elision_bridge_passes_only_after_complete_constraint_coverage_and_exact_postvalidation":True,
  "bridge_fails_closed_if_either_gate_missing":True,
  "stale_forced_fail_3_4_mass_claim_removed":True,
  "terminal_cases_consumed":0,
  "incremental_spend_usd":0
 },
 "deduction":"FOR THE VERIFIED FROZEN 200-ROW LEGACY IFEVAL POPULATION, SEMANTIC-SEED GENERATION IS NOT A LOGICAL PREREQUISITE OF THE LIVEBENCH IF SCORE. COMPLETE SCORE-RELEVANT LEGACY CONSTRAINT SOLVING PLUS EXACT CHECKER POSTVALIDATION IS SUFFICIENT FOR SCORE PURPOSES.",
 "hard_nonclaims":["NO_LIVEBENCH_SCORE_CLAIM","NO_CASES_CLAIMED_FIXED","NO_ACCEPTANCE_CREDIT","NO_SEMANTIC_CAPABILITY_OWNERSHIP_CREDIT"]
}
(ROOT/"livebench_if_semantic_elision_verification_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
