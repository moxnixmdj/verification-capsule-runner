from __future__ import annotations
import hashlib
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_constraint_compiler_v2_20261004"
EXPECTED={
    "instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
    "instruction_constraint_compiler_v2.py":"c93add618e2a2cde56df002e438433edcfe9b9e0",
    "test_instruction_constraint_compiler_v2.py":"096f92efe9b64a4f246ce550fbbeecb7acb0f552",
}

def git_blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for name,expected in EXPECTED.items():
    path=SUB/name
    if not path.is_file():
        raise SystemExit("FAIL_CLOSED:MISSING_SUBJECT:"+name)
    observed=git_blob(path)
    if observed!=expected:
        raise SystemExit("FAIL_CLOSED:BLOB_DRIFT:"+name+":"+observed)

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL_CLOSED:IMPORT_SPEC:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

v1=load("canonical.runtime.instruction_constraint_compiler_v1",SUB/"instruction_constraint_compiler_v1.py")
runtime.instruction_constraint_compiler_v1=v1
v2=load("canonical.runtime.instruction_constraint_compiler_v2",SUB/"instruction_constraint_compiler_v2.py")
runtime.instruction_constraint_compiler_v2=v2
tests=load("subject_constraint_compiler_v2_tests",SUB/"test_instruction_constraint_compiler_v2.py")

suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
if not result.wasSuccessful():
    print(stream.getvalue())
    raise SystemExit("FAIL_CLOSED:SUBJECT_TEST_FAILURE")

# Fresh parameterized challenges not present as literals in the subject test file.
fresh=[
    "Write the entire response in title case. Use exactly 3 words.",
    "Include at least 7 personal pronouns.",
    "Each sentence must contain exactly 4 more words than the previous one.",
    "Include keyword 'quasar' in the 4-th sentence.",
    "Include keyword 'nebula' in the 3-th sentence, as the 5-th word of that sentence.",
    "The second word in your response and the second to last word in your response should be the word 'vector'.",
]
fresh_results=[]
for prompt in fresh:
    out=v2.synthesize_formal_v2(prompt)
    if out.get("status")!="FORMAL_CONSTRAINTS_SATISFIED":
        raise SystemExit("FAIL_CLOSED:FRESH_SYNTHESIS:"+prompt+":"+json.dumps(out,sort_keys=True))
    program=v2.compile_program(prompt)
    ok,errors=v2.validate_program(out.get("response") or "",program)
    if not ok:
        raise SystemExit("FAIL_CLOSED:FRESH_POSTVALIDATION:"+prompt+":"+repr(errors))
    fresh_results.append({"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),"pass":True})

# Architecture guard: this candidate must remain benchmark-agnostic and cannot
# read hidden evaluation metadata.
source=(SUB/"instruction_constraint_compiler_v2.py").read_text(encoding="utf-8")
for forbidden in ("LIVEBENCH","question_id","instruction_id_list","benchmark_id","task_id"):
    if forbidden in source:
        raise SystemExit("FAIL_CLOSED:BENCHMARK_SPECIFIC_DEPENDENCY:"+forbidden)

print(json.dumps({
    "schema":"PROJECT_BRAIN_INSTRUCTION_CONSTRAINT_COMPILER_V2_INDEPENDENT_DIAGNOSTIC",
    "status":"PASS",
    "exact_subject_blobs":True,
    "subject_tests_run":result.testsRun,
    "subject_failures":len(result.failures),
    "subject_errors":len(result.errors),
    "fresh_generalization_challenges":fresh_results,
    "benchmark_specific_dependency_scan":"PASS",
    "terminal_case_content_read":False,
    "terminal_cases_consumed":0,
    "paid_external_model_or_api_used":False,
    "acceptance_credit_delta":0,
},sort_keys=True))
