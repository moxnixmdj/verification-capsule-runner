#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"general_literal_response_v1"
EXPECTED={
 "canonical/governance/GENERAL_LITERAL_RESPONSE_PREEXPOSURE_V1.json":"ab41f6a5476015b1e008cd4affc1b0505666ba20",
 "canonical/runtime/general_literal_response_v1.py":"5297725c84348403ea9286dd2211ed82406e3558",
 "canonical/runtime/astra_runtime.py":"ea2fbdc8a5ebba39827e8a162124459bc10e8180",
 "canonical/tests/test_general_literal_response_v1.py":"5bea2eebe24b4d784aa51f7e974eb45f16240954",
}
def blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for rel,want in EXPECTED.items():
    p=SUBJECT/rel
    assert p.is_file(),f"MISSING:{rel}"
    assert blob(p)==want,(rel,blob(p),want)

# The observed LiveBench zero-case token was not part of preexposure or implementation.
for rel in EXPECTED:
    assert "SYNTHETIC_OK" not in (SUBJECT/rel).read_text(encoding="utf-8"),rel

env=dict(__import__("os").environ)
env["PYTHONPATH"]=str(SUBJECT)
tests=subprocess.run(
    [sys.executable,"-m","unittest","canonical.tests.test_general_literal_response_v1","-v"],
    cwd=SUBJECT,env=env,text=True,capture_output=True,timeout=120,
)
print(tests.stdout)
print(tests.stderr)
assert tests.returncode==0,"PREEXPOSURE_TEST_FAILURE"

sys.path.insert(0,str(SUBJECT))
sys.path.insert(0,str(SUBJECT/"canonical"/"runtime"))
from canonical.runtime import astra_runtime
from canonical.runtime.general_literal_response_v1 import parse_literal_response_instruction

# Previously failing synthetic zero-case is used only now, after code is frozen.
instruction="Reply with exactly SYNTHETIC_OK."
out=astra_runtime.run_goal(
    {
      "goal_ref":"goal",
      "allow_optional_model_planner":False,
      "max_controller_actions":4,
      "max_cycles":2,
    },
    {"mission_id":"ROOT2-LIVEBENCH-IF-INFERENCE-ZERO-CASE-HOLDOUT","goal":instruction},
)
assert out["stdout"]=="SYNTHETIC_OK.",out
assert out["final_summary"]=="SYNTHETIC_OK.",out
assert out["cognition_dependency_class"]=="MODEL_INDEPENDENT",out
assert out["model_dependency_count"]==0,out
contract=out["literal_response_contract"]
assert contract["external_frontier_model_calls"]==0
assert contract["network_calls"]==0
assert contract["tool_calls"]==0

# Additional post-freeze holdout checks class generality and fail-closed boundary.
extra=astra_runtime.run_goal(
    {"goal_ref":"goal","allow_optional_model_planner":False},
    {"mission_id":"GENERAL-LITERAL-HOLDOUT","goal":"Please emit exactly \"late holdout phrase\""},
)
assert extra["stdout"]=="late holdout phrase"
assert extra["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert parse_literal_response_instruction(
    "If ready, reply with exactly SHOULD_NOT_ROUTE"
) is None

receipt={
 "schema":"PROJECT_BRAIN_GENERAL_LITERAL_RESPONSE_PUBLIC_RUNNER_RESULT_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
 "preexposure_positive_count":8,
 "preexposure_negative_count":8,
 "previously_failing_synthetic_holdout":"PASS",
 "additional_postfreeze_holdout":"PASS",
 "terminal_case_content_read":False,
 "terminal_cases_consumed":0,
 "external_frontier_model_calls":0,
 "network_calls":0,
 "tool_calls":0,
 "persistent_learned_bytes":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
}
print("GENERAL_LITERAL_RESPONSE_RECEIPT="+json.dumps(receipt,sort_keys=True))
print("PASS: bounded literal-response route generalizes to post-freeze zero-case holdout")
