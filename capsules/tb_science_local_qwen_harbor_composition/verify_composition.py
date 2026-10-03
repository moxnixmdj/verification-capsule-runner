from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
CURRENT=ROOT/"current"
PRIOR=ROOT/"prior"
EVIDENCE=ROOT/"evidence"

current_agent=(CURRENT/"canonical/runtime/harbor_science_agent_v1.py").read_text(encoding="utf-8")
prior_agent=(PRIOR/"harbor_science_agent_v1.py").read_text(encoding="utf-8")

normalized=current_agent
replacements=[
    ("Return one structured proposal object only.", "Return one JSON object only."),
    ("science_planner.plan(prompt, timeout_s=180)", "science_planner.plan(prompt, timeout_s=20)"),
    ('return "1.2.0"', 'return "1.1.0"'),
]
for new, old in replacements:
    if new not in normalized:
        raise AssertionError("CURRENT_CONTROLLER_EXPECTED_DIFFERENCE_MISSING:"+new)
    normalized=normalized.replace(new,old,1)
assert normalized==prior_agent, "CURRENT_CONTROLLER_HAS_UNPROVED_DIFFERENCES_BEYOND_FROZEN_THREE"

prior_receipt=json.loads((EVIDENCE/"TB_SCIENCE_DEDICATED_PLANNER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())
local_receipt=json.loads((EVIDENCE/"TB_SCIENCE_LOCAL_QWEN_PLANNER_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())

assert "PASS" in prior_receipt["status"]
assert prior_receipt["exact_brain_blobs"]["canonical/runtime/harbor_science_agent_v1.py"]=="8ab8287fdb6a9b63b9fe2d2addde731486c89d1e"
assert "REAL_HARBOR_0_23_0_CUSTOM_AGENT_BINDING_PASS" in prior_receipt["verified"]
assert "BRAIN_DETERMINISTIC_TERMINALIZATION_PRESERVED" in prior_receipt["verified"]
assert "ZERO_TERMINAL_CASE_EXPOSURE" in prior_receipt["verified"]

assert "PASS" in local_receipt["status"]
assert local_receipt["exact_brain_blobs"]["canonical/runtime/harbor_science_agent_v1.py"]=="5557efd21f1a433ad16766def3775a79c459784b"
assert local_receipt["exact_brain_blobs"]["canonical/runtime/harbor_science_planner_v1.py"]=="879887984e2ca8abacac486d687f519f5d0d78a5"
assert local_receipt["live_proposal_contract"]["passes"]==6
assert local_receipt["live_proposal_contract"]["required_passes"]==6
assert "REAL_CONTROLLER_CONTRACT_PARSER_ACCEPTS_ALL_SIX_PROPOSALS" in local_receipt["verified"]
assert "ZERO_TERMINAL_TASK_EXPOSURE" in local_receipt["verified"]

import sys
sys.path.insert(0,str(CURRENT))
from harbor.agents.base import BaseAgent
from canonical.runtime import harbor_science_agent_v1 as science

assert issubclass(science.HarborScienceAgent,BaseAgent)
assert science.HarborScienceAgent.name()=="project-brain-science"
assert science.HarborScienceAgent().version()=="1.2.0"

class Receipt:
    def __init__(self,returncode=0,stdout="",stderr=""):
        self.returncode=returncode
        self.stdout=stdout
        self.stderr=stderr

class SyntheticHarborEnv:
    def __init__(self):
        self.commands=[]
    async def exec(self,command,timeout_sec=None,**kwargs):
        self.commands.append((command,timeout_sec))
        return Receipt(0,"ok","")

def proposal(prompt,timeout_s=180):
    assert timeout_s==180
    return {
        "text":json.dumps({
            "material_requirements":["R1"],
            "candidates":[{
                "action_id":"A1",
                "covers":["R1"],
                "command":"printf ok > /tmp/project_brain_science_canary",
                "verify_command":"test -s /tmp/project_brain_science_canary",
            }],
        }),
        "model":"brain-qwen3.5-9b",
        "transport":"PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL",
    }

env=SyntheticHarborEnv()
with patch.object(science.science_planner,"plan",proposal):
    result=asyncio.run(science.run_science_goal("synthetic harbor composition canary",env,max_cycles=1))

assert result["status"]=="FINISHED",result
assert result["finish_authority"]=="BRAIN_VERIFIED_STATE",result
assert result["model_has_terminal_authority"] is False,result
assert result["material_requirements"]==["R1"],result
assert result["resolved_requirements"]==["R1"],result
assert result["cycles"]==1,result
assert [c for c,_ in env.commands]==[
    "printf ok > /tmp/project_brain_science_canary",
    "test -s /tmp/project_brain_science_canary",
],env.commands

print(json.dumps({
    "schema":"PROJECT_BRAIN_TB_SCIENCE_LOCAL_QWEN_HARBOR_COMPOSITION_PREFLIGHT_V1",
    "status":"PASS",
    "proof_kind":"EXACT_DIFFERENTIAL_COMPOSITION_PLUS_FRESH_HARBOR_0_23_IMPORT_AND_SYNTHETIC_CONTROL_EXECUTION",
    "current_controller_blob":"5557efd21f1a433ad16766def3775a79c459784b",
    "prior_real_harbor_verified_controller_blob":"8ab8287fdb6a9b63b9fe2d2addde731486c89d1e",
    "current_planner_blob":"879887984e2ca8abacac486d687f519f5d0d78a5",
    "exact_controller_delta":[
        "PROMPT_JSON_OBJECT_WORDING_TO_STRUCTURED_PROPOSAL_OBJECT",
        "PLANNER_TIMEOUT_20_TO_180_SECONDS",
        "AGENT_VERSION_1_1_0_TO_1_2_0"
    ],
    "all_other_controller_bytes_identical_after_normalization":True,
    "prior_real_harbor_binding_receipt":"TB_SCIENCE_DEDICATED_PLANNER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
    "current_local_qwen_receipt":"TB_SCIENCE_LOCAL_QWEN_PLANNER_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
    "harbor_version":"0.23.0",
    "harbor_base_agent_subclass":True,
    "synthetic_action_verify_finish_pass":True,
    "brain_finish_authority":"BRAIN_VERIFIED_STATE",
    "model_terminal_authority":False,
    "terminal_task_content_read":0,
    "terminal_trials_executed":0,
    "incremental_spend_usd":0,
    "execution_authority":False,
    "promotion_authority":False,
    "capability_credit_delta":0,
    "family_credit_delta":0
},sort_keys=True))
