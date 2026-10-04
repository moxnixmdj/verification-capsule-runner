from __future__ import annotations
import copy, hashlib, importlib.metadata, json, os, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/livebench_precommit_v3_20261004"
V2=SUB/"LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json"
V3=SUB/"LIVEBENCH_IF_EXECUTION_PRECOMMIT_V3.json"
SUP=SUB/"LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_V1.json"
SUPV=SUB/"LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
FAIL=SUB/"LIVEBENCH_FIRST_DIRECT_ATTEMPT_TRUTH_RECEIPT_20261004_V1.json"
EXPECTED={
 V2:"66554061f204d8a86b37a30c84d0cf07a525a786",
 V3:"bb7c5694c7263b9216be8bd462227781e28b07b8",
 SUP:"13105f751550ea89646bb82bd4c1d8325afe2840",
 SUPV:"8282b4fe307020fef13ac6421262c18ce7f8c0e8",
 FAIL:"0ddffd52cd05b880964cf034527aabddb255baef",
}
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM={
 "livebench/gen_ground_truth_judgment.py":"b36561da5b54380c724c507462d0ee65feefeac8",
 "livebench/if_runner/ifbench/evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
 "livebench/if_runner/ifbench/instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
 "livebench/if_runner/ifbench/instructions_registry.py":"adfed4832877566e62970257b50c6fa32c302fb2",
 "livebench/if_runner/ifbench/instructions_util.py":"21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
 "livebench/if_runner/instruction_following_eval/evaluation_main.py":"4a341984936c4d609644a3b77f8c030ac5aa7269",
 "livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
 "livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "livebench/if_runner/instruction_following_eval/instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
 "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
}
PYARROW_WHEEL_SHA256="b7ae0bbdc8c6674259b25bef5d2a1d6af5d39d7200c819cf99e07f7dfef1c51e"

def blob(p:pathlib.Path)->str:
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def digest(o)->str:
 return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def run(cmd,**kw):
 return subprocess.run(cmd,check=True,text=True,**kw)

for p,e in EXPECTED.items():
 assert blob(p)==e,(p,blob(p),e)

v2=json.loads(V2.read_text())
v3=json.loads(V3.read_text())
sup=json.loads(SUP.read_text())
supv=json.loads(SUPV.read_text())
failed=json.loads(FAIL.read_text())

assert v3["schema"]=="PROJECT_BRAIN_LIVEBENCH_IF_EXECUTION_PRECOMMIT_V3"
assert v3["candidate"]==v2["candidate"]
assert v3["harness"]==v2["harness"]
assert v3["policy"]==v2["policy"]
assert v3["component_sha256"]["candidate"]==v2["component_sha256"]["candidate"]
assert v3["component_sha256"]["harness"]==v2["component_sha256"]["harness"]
assert v3["component_sha256"]["policy"]==v2["component_sha256"]["policy"]

# Scorer delta is exactly the public upstream dispatch + legacy scorer files.
expected_scorer=copy.deepcopy(v2["scorer"])
expected_scorer["dispatch_source"]=[
 "livebench/gen_ground_truth_judgment.py",
 "b36561da5b54380c724c507462d0ee65feefeac8",
]
expected_scorer["dispatch_rule"]="category == instruction_following AND livebench_release_date < 2025-11-25 => legacy IFEval strict scorer; otherwise current IFBench strict scorer"
expected_scorer["legacy_files"]=[
 ["livebench/if_runner/instruction_following_eval/evaluation_main.py","4a341984936c4d609644a3b77f8c030ac5aa7269"],
 ["livebench/if_runner/instruction_following_eval/instructions_registry.py","903ed738398648c7cfac61d5ffa478c22f1f0891"],
 ["livebench/if_runner/instruction_following_eval/instructions.py","4997bab885a676d92545fd91a9a20b48d234a2b2"],
 ["livebench/if_runner/instruction_following_eval/instructions_util.py","1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"],
 ["livebench/process_results/instruction_following/utils.py","8ce01747887ec0792c8f024e1972e34ece781676"],
]
assert v3["scorer"]==expected_scorer

# Environment delta is exactly legacy scorer dependencies + pinned decoder and
# their zero-case receipts.
expected_env=copy.deepcopy(v2["environment"])
expected_env["packages"] += [
 ["langdetect","1.0.9",None],
 ["immutabledict","4.3.1",None],
 ["pandas","2.3.3",None],
 ["pyarrow","21.0.0",PYARROW_WHEEL_SHA256],
]
expected_env["parquet_reader_probe"]=v3["environment"]["parquet_reader_probe"]
expected_env["legacy_scorer_verification"]=v3["environment"]["legacy_scorer_verification"]
assert v3["environment"]==expected_env
assert v3["environment"]["parquet_reader_probe"]["workflow_run_id"]==37188489755
assert v3["environment"]["parquet_reader_probe"]["terminal_cases_consumed"]==0
assert v3["environment"]["legacy_scorer_verification"]["workflow_run_id"]==37188804615
assert v3["environment"]["legacy_scorer_verification"]["candidate_inferences"]==0

expected_digests={
 "candidate":"8f99aa371061160822670fc6f5da2ce3a01cc260063330ed6e5954a2cac68c9a",
 "harness":"dcb03697e0f38d50933ca38650809fc80343737e4be3105966f2851e510c4b9e",
 "scorer":"d2ba3bd54964cf842bd9dbe35d5f07239e28f1c6db61b07c72a95234276c0760",
 "environment":"87f38052cf500e0816b6b2c8f2a7c3b5b6d25efdeead77829f613c72ceb11664",
 "policy":"3e77340568dce7d6ff8f77f94de7e1fe38b85c705d88ba1067447f716a456e90",
}
for k,e in expected_digests.items():
 assert digest(v3[k])==e,(k,digest(v3[k]),e)
 assert v3["component_sha256"][k]==e

assert failed["status"].startswith("FAIL_CLOSED")
assert failed["observed"]["terminal_population_loaded"] is True
assert failed["observed"]["candidate_inference_count"]==0
assert failed["observed"]["candidate_response_count"]==0
assert failed["observed"]["livebench_score_exists"] is False
assert failed["failure"]["repair_boundary"]=="SCORER_DISPATCH_AND_SCORER_RUNTIME_DEPENDENCIES_ONLY"

assert supv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert supv["verified"]["terminal_case_content_read"] is False
assert supv["verified"]["candidate_inferences"]==0
assert supv["verified"]["exact_dispatch_rule_source_pass"] is True
assert v3["case_exposure"]["repair_derived_from_terminal_prompt_content"] is False
assert v3["case_exposure"]["repair_derived_from_candidate_response"] is False
assert v3["case_exposure"]["repair_derived_from_score"] is False
assert v3["execution_authority"] is False
assert v3["fresh_reality_authority"] is False
assert v3["promotion_authority"] is False

with tempfile.TemporaryDirectory(prefix="lb-v3-zero-") as td:
 base=pathlib.Path(td)
 wheel_dir=base/"wheel"; wheel_dir.mkdir()
 run([sys.executable,"-m","pip","download","--disable-pip-version-check","--quiet","--no-deps","--only-binary=:all:","--dest",str(wheel_dir),"pyarrow==21.0.0"])
 wheels=list(wheel_dir.iterdir())
 assert len(wheels)==1,wheels
 assert hashlib.sha256(wheels[0].read_bytes()).hexdigest()==PYARROW_WHEEL_SHA256
 run([sys.executable,"-m","pip","install","--disable-pip-version-check","--quiet",str(wheels[0]),
      "nltk==3.10.3","emoji==2.16.0","syllapy==0.7.2","setuptools==80.9.0",
      "spacy==3.8.16",
      "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
      "langdetect==1.0.9","immutabledict==4.3.1","pandas==2.3.3"])
 assert importlib.metadata.version("pyarrow")=="21.0.0"
 repo=base/"LiveBench"
 run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(repo)])
 run(["git","-C",str(repo),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT])
 run(["git","-C",str(repo),"checkout","--quiet","--detach",LIVEBENCH_COMMIT])
 for p,e in UPSTREAM.items():
  got=run(["git","-C",str(repo),"rev-parse",f"HEAD:{p}"],capture_output=True).stdout.strip()
  assert got==e,(p,got,e)
 dispatch=(repo/"livebench/gen_ground_truth_judgment.py").read_text()
 assert 'm.question.get(\'category\') == \'instruction_following\' and m.question.get("livebench_release_date", "") < "2025-11-25"' in dispatch
 sys.path.insert(0,str(repo/"livebench/if_runner"))
 from instruction_following_eval import evaluation_main as legacy_eval
 legacy=legacy_eval.InputExample(key=1,instruction_id_list=["punctuation:no_comma"],prompt="synthetic legacy prompt",kwargs=[{}])
 lo=legacy_eval.test_instruction_following_strict(legacy,{"synthetic legacy prompt":"hello world"})
 assert lo.follow_all_instructions is True and lo.follow_instruction_list==[True]
 sys.path.insert(0,str(repo))
 from livebench.if_runner.ifbench import evaluation_lib as current_eval
 modern=current_eval.InputExample(key=2,instruction_id_list=["format:no_whitespace"],prompt="synthetic modern prompt",kwargs=[{}])
 mo=current_eval.test_instruction_following_strict(modern,"helloworld")
 assert mo.follow_all_instructions is True and mo.follow_instruction_list==[True]

print(json.dumps({
 "schema":"PROJECT_BRAIN_LIVEBENCH_IF_PRECOMMIT_V3_PUBLIC_VERIFIER_V1",
 "status":"PASS",
 "exact_subject_blobs":len(EXPECTED),
 "candidate_component_unchanged":True,
 "harness_component_unchanged":True,
 "policy_component_unchanged":True,
 "scorer_delta_exact_and_public":True,
 "environment_delta_exact":True,
 "pyarrow_wheel_sha256":PYARROW_WHEEL_SHA256,
 "legacy_strict_synthetic_pass":True,
 "ifbench_strict_synthetic_pass":True,
 "terminal_case_content_read":False,
 "new_candidate_inferences":0,
 "execution_authority":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
