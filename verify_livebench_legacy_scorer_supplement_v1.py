from __future__ import annotations
import hashlib, importlib.metadata, json, os, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/livebench_legacy_scorer_supplement_v1/LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_V1.json"
EXPECTED_SUBJECT="13105f751550ea89646bb82bd4c1d8325afe2840"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
FILES={
 "livebench/gen_ground_truth_judgment.py":"b36561da5b54380c724c507462d0ee65feefeac8",
 "livebench/if_runner/instruction_following_eval/evaluation_main.py":"4a341984936c4d609644a3b77f8c030ac5aa7269",
 "livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
 "livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "livebench/if_runner/instruction_following_eval/instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
 "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
}
def blob(p:pathlib.Path)->str:
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def run(cmd,**kw): return subprocess.run(cmd,check=True,text=True,**kw)
def main():
 assert os.environ.get("GITHUB_ACTIONS")=="true"
 assert str(os.environ.get("REPOSITORY_PRIVATE","")).lower()=="false"
 assert sys.version_info[:2]==(3,12)
 assert blob(SUB)==EXPECTED_SUBJECT
 m=json.loads(SUB.read_text())
 assert m["derivation_independence"]["terminal_prompt_content_used_to_design_repair"] is False
 assert m["derivation_independence"]["candidate_response_used_to_design_repair"] is False
 assert m["derivation_independence"]["score_used_to_design_repair"] is False
 run([sys.executable,"-m","pip","install","--disable-pip-version-check","--quiet",
      "langdetect==1.0.9","immutabledict==4.3.1","pandas==2.3.3"])
 versions={x:importlib.metadata.version(x) for x in ("langdetect","immutabledict","pandas")}
 assert versions=={"langdetect":"1.0.9","immutabledict":"4.3.1","pandas":"2.3.3"}
 with tempfile.TemporaryDirectory(prefix="lb-legacy-zero-") as td:
  repo=pathlib.Path(td)/"LiveBench"
  run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(repo)])
  run(["git","-C",str(repo),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT])
  run(["git","-C",str(repo),"checkout","--quiet","--detach",LIVEBENCH_COMMIT])
  for p,e in FILES.items():
   got=run(["git","-C",str(repo),"rev-parse",f"HEAD:{p}"],capture_output=True).stdout.strip()
   assert got==e,(p,got,e)
  dispatch=(repo/"livebench/gen_ground_truth_judgment.py").read_text()
  assert 'm.question.get(\'category\') == \'instruction_following\' and m.question.get("livebench_release_date", "") < "2025-11-25"' in dispatch
  sys.path.insert(0,str(repo/"livebench/if_runner"))
  from instruction_following_eval import evaluation_main as legacy_eval
  legacy=legacy_eval.InputExample(
      key=1,
      instruction_id_list=["punctuation:no_comma"],
      prompt="synthetic legacy prompt",
      kwargs=[{}],
  )
  lo=legacy_eval.test_instruction_following_strict(legacy,{"synthetic legacy prompt":"hello world"})
  assert lo.follow_all_instructions is True and lo.follow_instruction_list==[True]
  sys.path.insert(0,str(repo))
  from livebench.if_runner.ifbench import evaluation_lib as ifb
  modern=ifb.InputExample(
      key=2,
      instruction_id_list=["format:no_whitespace"],
      prompt="synthetic modern prompt",
      kwargs=[{}],
  )
  mo=ifb.test_instruction_following_strict(modern,"helloworld")
  assert mo.follow_all_instructions is True and mo.follow_instruction_list==[True]
 print(json.dumps({
   "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_PUBLIC_VERIFIER_V1",
   "status":"PASS",
   "exact_upstream_blob_count":len(FILES),
   "legacy_strict_synthetic_pass":True,
   "ifbench_strict_synthetic_pass":True,
   "dispatch_rule_exact_source_pass":True,
   "package_versions":versions,
   "terminal_case_content_read":False,
   "terminal_cases_consumed":0,
   "candidate_inferences":0,
   "candidate_mutation":False,
   "fresh_reality_authority":False,
   "acceptance_credit_delta":0
 },sort_keys=True))
 return 0
if __name__=="__main__": raise SystemExit(main())
