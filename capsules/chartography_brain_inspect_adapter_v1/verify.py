#!/usr/bin/env python3
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
R=ROOT/"canonical/runtime/eval_adapters/chartography_brain_model_api_v1.py"
T=ROOT/"canonical/tests/test_chartography_brain_model_api_v1.py"
G=ROOT/"canonical/governance/CHARTOGRAPHY_BRAIN_INSPECT_ADAPTER_V1.json"

def git_blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

expected={
  "runtime":"2d58a2937e8d5a6b41c29f7f92fff3d10f88e025",
  "tests":"21bcebc8aa3059fe6f4d1d2eb9fffb609aea99e1",
  "governance":"f0352c187eb921d6e736608825005df887449488",
}
actual={"runtime":git_blob(R),"tests":git_blob(T),"governance":git_blob(G)}
assert actual==expected,(actual,expected)
assert importlib.metadata.version("inspect-ai")=="0.3.276"

g=json.loads(G.read_text())
assert g["status"].startswith("CANDIDATE__FAIL_CLOSED_INSPECT_MODELAPI_ADAPTER")
assert g["backend_binding_contract"]["current_state"]=="OPEN"
assert g["classification"]["root1"].startswith("UNCHANGED_INACTIVE")
assert g["terminal_cases_consumed"]==0
assert g["acceptance_credit_delta"]==0

proc=subprocess.run(
    [sys.executable,"-m","unittest","-v","canonical.tests.test_chartography_brain_model_api_v1"],
    cwd=ROOT,text=True,capture_output=True
)
print(proc.stdout)
print(proc.stderr,file=sys.stderr)
assert proc.returncode==0,proc.returncode
combined=proc.stdout+"\n"+proc.stderr
assert "Ran 11 tests" in combined

print(json.dumps({
  "schema":"PROJECT_BRAIN_CHARTOGRAPHY_BRAIN_INSPECT_ADAPTER_PUBLIC_RUNNER_RESULT_V1",
  "pass":True,
  "status":"PASS__INSPECT_AI_0_3_276__11_OF_11_ADAPTER_TESTS__EXACT_QUESTION_IMAGE_BYTES__FAIL_CLOSED_BACKEND__ZERO_CASES__ZERO_CREDIT",
  "inspect_ai_version":"0.3.276",
  "tests_passed":11
},sort_keys=True))
