#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
S=ROOT/"subject"/"general_literal_response_v1"
EXPECTED={
"canonical/governance/GENERAL_LITERAL_RESPONSE_PREEXPOSURE_V1.json":"ab41f6a5476015b1e008cd4affc1b0505666ba20",
"canonical/runtime/general_literal_response_v1.py":"5297725c84348403ea9286dd2211ed82406e3558",
"canonical/runtime/astra_runtime.py":"ea2fbdc8a5ebba39827e8a162124459bc10e8180",
"canonical/tests/test_general_literal_response_v1.py":"5bea2eebe24b4d784aa51f7e974eb45f16240954",
}
def blob(p):
    d=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
for rel,want in EXPECTED.items():
    p=S/rel
    assert p.is_file() and blob(p)==want,(rel,blob(p) if p.exists() else None,want)

holdout="SYNTHETIC"+"_"+"OK"
pre=json.loads((S/"canonical/governance/GENERAL_LITERAL_RESPONSE_PREEXPOSURE_V1.json").read_text())
for task in pre["positive_tasks"]+pre["negative_tasks"]:
    assert holdout not in task["instruction"]
    assert holdout not in str(task.get("expected",""))
for rel in (
 "canonical/runtime/general_literal_response_v1.py",
 "canonical/runtime/astra_runtime.py",
 "canonical/tests/test_general_literal_response_v1.py",
):
    assert holdout not in (S/rel).read_text()

env=dict(os.environ); env["PYTHONPATH"]=str(S)
t=subprocess.run(
 [sys.executable,"-m","unittest","canonical.tests.test_general_literal_response_v1","-v"],
 cwd=S,env=env,text=True,capture_output=True,timeout=120
)
print(t.stdout); print(t.stderr)
assert t.returncode==0

sys.path.insert(0,str(S)); sys.path.insert(0,str(S/"canonical"/"runtime"))
from canonical.runtime import astra_runtime
from canonical.runtime.general_literal_response_v1 import parse_literal_response_instruction

instruction="Reply with exactly "+holdout+"."
out=astra_runtime.run_goal(
 {"goal_ref":"goal","allow_optional_model_planner":False,"max_controller_actions":4,"max_cycles":2},
 {"mission_id":"ZERO-CASE-HOLDOUT","goal":instruction},
)
assert out["stdout"]==holdout+"."
assert out["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert out["model_dependency_count"]==0
assert out["literal_response_contract"]["tool_calls"]==0
assert out["literal_response_contract"]["network_calls"]==0

extra=astra_runtime.run_goal(
 {"goal_ref":"goal","allow_optional_model_planner":False},
 {"mission_id":"POSTFREEZE-HOLDOUT","goal":"Please emit exactly \"late holdout phrase\""},
)
assert extra["stdout"]=="late holdout phrase"
assert extra["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert parse_literal_response_instruction("If ready, reply with exactly X") is None

print("PASS: 8 positive + 8 negative preexposure cases and post-freeze holdouts pass; zero terminal cases/models/network/tools/spend")
