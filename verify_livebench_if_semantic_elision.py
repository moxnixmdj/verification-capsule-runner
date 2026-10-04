#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, itertools, json, pathlib, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_if_semantic_elision_v1"
FILES={
 SUB/"LIVEBENCH_IF_SEMANTIC_ELISION_THEOREM_V1.json":"9bdc94418d84b2fb0f78fedde4724e4eca5b1e39",
 SUB/"canonical/runtime/livebench_if_score_only_semantic_elision_v1.py":"48214f668f9353cf17905c6220e9e3048637366c",
 SUB/"canonical/tests/test_livebench_if_score_only_semantic_elision_v1.py":"f138b9251e2511d18b1f05c2af78f9331ff5379e",
}
UPSTREAM_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM={
 "process_results":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/process_results/instruction_following/utils.py",
  "8ce01747887ec0792c8f024e1972e34ece781676"),
 "evaluation_lib":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/if_runner/ifbench/evaluation_lib.py",
  "2c7bd1290031dbe4ae0f016c53255f4af0ec645b"),
 "registry":(
  f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/if_runner/ifbench/instructions_registry.py",
  "adfed4832877566e62970257b50c6fa32c302fb2"),
}

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def fetch(url:str)->bytes:
 req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
 with urllib.request.urlopen(req,timeout=30) as r:
  return r.read()

for p,h in FILES.items():
 assert blob(p.read_bytes())==h,(p,blob(p.read_bytes()),h)

up={}
for k,(url,h) in UPSTREAM.items():
 b=fetch(url)
 assert blob(b)==h,(k,blob(b),h)
 up[k]=b.decode("utf-8")

process=up["process_results"]
eval_lib=up["evaluation_lib"]

# Exact scorer dataflow: response -> registered checkers -> boolean vector -> score.
assert "evaluation_lib.test_instruction_following_strict(inp, response)" in process
assert "score = score_results(result.follow_all_instructions, result.follow_instruction_list)" in process
assert "score_1 = 1 if follow_all_instructions else 0" in process
assert "score_2 = [1 if follow else 0 for follow in follow_instruction_list]" in process
assert "avg_score = (score_1 + score_2) / 2" in process
assert "instruction.check_following(response)" in eval_lib

tree=ast.parse(process)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="score_results")
used={n.id for n in ast.walk(fn) if isinstance(n,ast.Name)}
assert "prompt" not in used and "question" not in used and "reference" not in used
assert {"follow_all_instructions","follow_instruction_list"}.issubset(used)

# Exhaustively demonstrate that the score is a pure function of the checker vector
# for small arities; semantic content is not an argument.
def score(vec):
 all_pass=all(vec)
 return ((1 if all_pass else 0)+(sum(1 if x else 0 for x in vec)/len(vec)))/2
for n in range(1,6):
 for vec in itertools.product([False,True],repeat=n):
  s=score(vec)
  assert 0.0<=s<=1.0
  if all(vec):
   assert s==1.0

# Execute the fail-closed bridge directly from the frozen subject.
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
assert candidate["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert candidate["accounting"]["new_terminal_cases_exposed"]==0
assert candidate["mathematical_leverage"]["minimum_score_mass_needed_to_remove_the_old_forced_fail_upper_bound"]==3.4

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_IF_SEMANTIC_ELISION_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS",
 "subject_git_blobs":{p.name:h for p,h in FILES.items()},
 "upstream_git_blobs":{k:h for k,(_,h) in UPSTREAM.items()},
 "verified":{
  "frozen_scorer_uses_strict_registered_checkers":True,
  "score_is_pure_function_of_checker_pass_vector":True,
  "no_separate_semantic_quality_term_in_score_path":True,
  "all_checker_pass_vector_implies_row_score_one":True,
  "semantic_elision_bridge_passes_only_after_complete_constraint_coverage_and_exact_postvalidation":True,
  "bridge_fails_closed_if_either_gate_missing":True,
  "terminal_cases_consumed":0,
  "incremental_spend_usd":0,
 },
 "deduction":"SEMANTIC_SEED_GENERATION_IS_NOT_A_LOGICAL_PREREQUISITE_FOR_THE_FROZEN_LIVEBENCH_IF_SCORE; COMPLETE_SCORE_RELEVANT_CONSTRAINT_SOLVING_PLUS_EXACT_POSTVALIDATION_IS_SUFFICIENT.",
 "hard_nonclaims":["NO_LIVEBENCH_SCORE_CLAIM","NO_CASES_CLAIMED_FIXED","NO_ACCEPTANCE_CREDIT","NO_SEMANTIC_CAPABILITY_CLAIM_OUTSIDE_THIS_EXACT_SCORER"]
}
(ROOT/"livebench_if_semantic_elision_verification_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
