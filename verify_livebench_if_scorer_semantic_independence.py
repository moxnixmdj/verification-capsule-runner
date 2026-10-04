#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, urllib.request
from pathlib import Path

SOURCES={
 "process_results":(
  "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/process_results/instruction_following/utils.py",
  "8ce01747887ec0792c8f024e1972e34ece781676"),
 "modern_eval":(
  "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/evaluation_lib.py",
  "2c7bd1290031dbe4ae0f016c53255f4af0ec645b"),
 "modern_registry":(
  "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions_registry.py",
  "adfed4832877566e62970257b50c6fa32c302fb2"),
 "legacy_eval":(
  "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/instruction_following_eval/evaluation_main.py",
  "4a341984936c4d609644a3b77f8c030ac5aa7269"),
}

def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read()

def git_blob_sha(b):
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fn(tree,name):
 xs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
 assert len(xs)==1,(name,len(xs))
 return xs[0]

def calls(node):
 out=[]
 for n in ast.walk(node):
  if isinstance(n,ast.Call):
   if isinstance(n.func,ast.Name): out.append(n.func.id)
   elif isinstance(n.func,ast.Attribute):
    parts=[];x=n.func
    while isinstance(x,ast.Attribute):parts.append(x.attr);x=x.value
    if isinstance(x,ast.Name):parts.append(x.id)
    out.append(".".join(reversed(parts)))
 return out

def main():
 data={}; texts={}
 for key,(url,expected) in SOURCES.items():
  b=fetch(url); actual=git_blob_sha(b); assert actual==expected,(key,actual,expected)
  data[key]={"git_blob_sha":actual}; texts[key]=b.decode("utf-8")

 pr_tree=ast.parse(texts["process_results"])
 score=fn(pr_tree,"score_results")
 score_calls=set(calls(score))
 assert score_calls <= {"sum","len"}, score_calls
 src=ast.get_source_segment(texts["process_results"],score) or ""
 assert "follow_all_instructions" in src and "follow_instruction_list" in src
 assert "avg_score = (score_1 + score_2) / 2" in src
 assert "return avg_score" in src

 modern_proc=fn(pr_tree,"ifbench_process_results")
 modern_src=ast.get_source_segment(texts["process_results"],modern_proc) or ""
 assert "evaluation_lib.test_instruction_following_strict(inp, response)" in modern_src
 assert "score_results(result.follow_all_instructions, result.follow_instruction_list)" in modern_src

 legacy_proc=fn(pr_tree,"instruction_following_process_results")
 legacy_src=ast.get_source_segment(texts["process_results"],legacy_proc) or ""
 assert 'results = results["strict"]' in legacy_src
 assert "score_results(follow_all_instructions, follow_instruction_list)" in legacy_src

 modern_tree=ast.parse(texts["modern_eval"])
 strict=fn(modern_tree,"test_instruction_following_strict")
 strict_src=ast.get_source_segment(texts["modern_eval"],strict) or ""
 assert "instruction.check_following(response)" in strict_src
 assert "follow_all_instructions=all(is_following_list)" in strict_src
 assert "follow_instruction_list=is_following_list" in strict_src

 legacy_tree=ast.parse(texts["legacy_eval"])
 legacy_strict=fn(legacy_tree,"test_instruction_following_strict")
 legacy_strict_src=ast.get_source_segment(texts["legacy_eval"],legacy_strict) or ""
 assert "instruction.check_following(response)" in legacy_strict_src
 assert "follow_all_instructions=all(is_following_list)" in legacy_strict_src
 assert "follow_instruction_list=is_following_list" in legacy_strict_src

 combined="\n".join([src,modern_src,legacy_src,strict_src,legacy_strict_src]).casefold()
 forbidden=["model_judge","llm_judge","reference_answer_quality","semantic_quality_score"]
 assert not any(x in combined for x in forbidden),[x for x in forbidden if x in combined]

 receipt={
  "schema":"PROJECT_BRAIN_LIVEBENCH_IF_SCORER_SEMANTIC_INDEPENDENCE_PUBLIC_VERIFICATION_V1",
  "status":"PASS",
  "source_blobs":data,
  "verified":{
   "score_results_depends_only_on_instruction_following_booleans":True,
   "modern_strict_path_uses_registered_checker_check_following":True,
   "legacy_strict_path_uses_registered_checker_check_following":True,
   "semantic_quality_term_present":False,
   "reference_answer_quality_term_present":False,
   "model_judge_term_present":False,
  },
  "conclusion":"FOR_THE_PINNED_FROZEN_PUBLIC_SCORER_PATH_A_RESPONSE_NEEDS_NO_SEPARATE_SEMANTIC_QUALITY_SEED_TO_EARN_SCORE_IF_IT_PASSES_THE_REGISTERED_CHECKERS",
  "hard_nonclaims":[
   "NO_PROOF_CURRENT_SUCCESSOR_RECOVERS_ALL_CHECKERS_OR_PARAMETERS",
   "NO_LIVEBENCH_ACCEPTANCE_SCORE",
   "NO_TERMINAL_CASE_CONTENT_READ",
   "NO_GENERAL_SEMANTIC_INSTRUCTION_FOLLOWING_CLAIM"
  ]
 }
 Path("livebench_if_scorer_semantic_independence_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
