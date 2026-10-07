from __future__ import annotations
import asyncio, json
from unittest.mock import patch
from canonical.runtime import harbor_science_agent_v1 as s

READY="SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER"

class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

def planner_once(payload):
    used=False
    def _plan(prompt, timeout_s=180):
        nonlocal used
        if used:
            raise AssertionError("planner called more than once in one-cycle replay")
        used=True
        return {"text":json.dumps(payload),"model":"synthetic-fixed-substrate"}
    return _plan

class Rank7WarningEnv:
    def __init__(self): self.commands=[]
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command=="rank7-malformed-heredoc-action":
            return Receipt(0,"bash: line 22: warning: here-document at line 1 delimited by end-of-file (wanted PYEOF)","")
        if command=="rank7-proposal-verify":
            raise AssertionError("proposal verifier ran after transport-integrity failure")
        return Receipt(1,"","unexpected:"+command)

class DeadControllerEnv:
    def __init__(self, fail_liveness_call):
        self.commands=[]; self.liveness_calls=0; self.fail_liveness_call=fail_liveness_call
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command in {"create-controller","proposal-verify"}: return Receipt(0,"ok","")
        if command.startswith("test -s /app/submission/controller.py"): return Receipt(0,"","")
        if command.startswith("python -m py_compile /app/submission/controller.py"): return Receipt(0,"","")
        if "PROJECT_BRAIN_CONTROLLER_LIVENESS_V1" in command:
            self.liveness_calls+=1
            if self.liveness_calls==self.fail_liveness_call:
                return Receipt(42,"","CONTROLLER_EXITED_BEFORE_INPUT")
            return Receipt(0,"","")
        return Receipt(0,"ok","")

rank7_payload={
 "material_requirements":["plant_model","plant_params","controller_api","scenarios_public"],
 "candidates":[{"action_id":"create_controller","covers":["plant_model","plant_params","controller_api","scenarios_public"],"command":"rank7-malformed-heredoc-action","verify_command":"rank7-proposal-verify"}],
}
rank7_goal="Create /app/submission/controller.py and /app/submission/design_report.json. The controller process reads one JSON line at a time from stdin."
env=Rank7WarningEnv()
with patch.object(s.science_planner,"plan",planner_once(rank7_payload)):
    out=asyncio.run(s.run_science_goal(rank7_goal,env,max_cycles=1))
assert out["status"]!=READY,out
assert out.get("task_completion_claimed") is False,out
assert out["resolved_requirements"]==[],out
sel=[x for x in out["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
assert sel["action_transport_clean"] is False,sel
assert sel["verify_result"] is None,sel
assert env.commands==["rank7-malformed-heredoc-action"],env.commands

dead_payload={
 "material_requirements":["R1","BRAIN_DELIVERABLE_01"],
 "candidates":[{"action_id":"create","covers":["R1","BRAIN_DELIVERABLE_01"],"command":"create-controller","verify_command":"proposal-verify"}],
}
dead_goal="Create /app/submission/controller.py. The controller process must read one JSON line at a time from stdin and remain available for commands."
env2=DeadControllerEnv(1)
with patch.object(s.science_planner,"plan",planner_once(dead_payload)):
    out2=asyncio.run(s.run_science_goal(dead_goal,env2,max_cycles=1))
assert out2["status"]!=READY,out2
assert out2.get("task_completion_claimed") is False,out2
assert "BRAIN_DELIVERABLE_01" not in out2["resolved_requirements"],out2
assert env2.liveness_calls==1,env2.commands

env3=DeadControllerEnv(2)
with patch.object(s.science_planner,"plan",planner_once(dead_payload)):
    out3=asyncio.run(s.run_science_goal(dead_goal,env3,max_cycles=1))
assert out3["status"]!=READY,out3
assert out3.get("task_completion_claimed") is False,out3
assert env3.liveness_calls==2,env3.commands
assert any(
 x.get("kind")=="BRAIN_DECLARED_OUTPUT_GATE_FAILED"
 and any(f.get("reason")=="INTERACTIVE_CONTROLLER_EXITED_BEFORE_INPUT" for f in x.get("failures",[]))
 for x in out3["trace"]
),out3

print(json.dumps({
 "schema":"PROJECT_BRAIN_TB_SCIENCE_RAW_TASK_CONTROLLER_LIVENESS_PUBLIC_REPLAY_V2",
 "status":"PASS",
 "lossless_raw_task_acceptance_remains_external_verifier_pending":True,
 "exact_rank7_transport_falsifier_blocks_before_proposal_verify":True,
 "dead_interactive_controller_blocks_deliverable_promotion":True,
 "dead_interactive_controller_blocks_final_output_gate":True,
 "terminal_task_exposure":0,
 "incremental_spend_usd":0,
},sort_keys=True))
