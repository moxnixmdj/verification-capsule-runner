from __future__ import annotations
import asyncio, hashlib, importlib.util, json, pathlib, sys, types

ROOT=pathlib.Path(__file__).resolve().parent
TARGET=ROOT/"harbor_science_agent_v1.py"
EXPECTED="5bc8ebac26bb7c809d4698f535eff43b667b30df"

raw=TARGET.read_bytes()
blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
assert blob==EXPECTED,(blob,EXPECTED)
compile(raw,str(TARGET),"exec")

canonical=types.ModuleType("canonical"); canonical.__path__=[]
runtime=types.ModuleType("canonical.runtime"); runtime.__path__=[]
planner=types.ModuleType("canonical.runtime.harbor_science_planner_v1")
policy=types.ModuleType("canonical.runtime.harbor_command_policy")
transport=types.ModuleType("canonical.runtime.harbor_environment_transport")
contract=types.ModuleType("canonical.runtime.lossless_raw_task_contract_v1")
localizer=types.ModuleType("canonical.runtime.raw_task_acceptance_residual_localizer_v1")

policy.validate_environment_command=lambda command: str(command)
class HarborEnvironmentTransport:
    def __init__(self,environment): self.environment=environment
    async def exec(self,command,timeout_sec=None): return await self.environment.exec(command,timeout_sec=timeout_sec)
transport.HarborEnvironmentTransport=HarborEnvironmentTransport

def compile_contract(goal,source_id=None,routing_target_effects=None):
    text=str(goal)
    digest=hashlib.sha256(text.encode()).hexdigest()
    return {
      "pass":True,
      "task_contract_sha256":digest,
      "acceptance_contract":{
        "required_obligation_ids":["RAW_1"],
        "obligations":[{"obligation_id":"RAW_1","segment_sha256":digest,"text":text}]
      }
    }
contract.compile_contract=compile_contract

def localize(task_contract):
    return {
      "pass":True,
      "accounted_obligation_count":1,
      "objective_route_obligation_count":0,
      "semantic_residual_obligation_count":1,
      "obligations":[{"obligation_id":"RAW_1","status":"SEMANTIC_RESIDUAL"}]
    }
localizer.localize=localize

sys.modules.update({
 "canonical":canonical,
 "canonical.runtime":runtime,
 "canonical.runtime.harbor_science_planner_v1":planner,
 "canonical.runtime.harbor_command_policy":policy,
 "canonical.runtime.harbor_environment_transport":transport,
 "canonical.runtime.lossless_raw_task_contract_v1":contract,
 "canonical.runtime.raw_task_acceptance_residual_localizer_v1":localizer,
})
runtime.harbor_science_planner_v1=planner

spec=importlib.util.spec_from_file_location("candidate",TARGET)
candidate=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate)

class Receipt:
    def __init__(self,returncode=0,stdout="",stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

class Env:
    def __init__(self): self.files=set(); self.commands=[]
    async def exec(self,command,timeout_sec=None,**kwargs):
        self.commands.append(command)
        if command=="CREATE_BOTH":
            self.files.update({"/app/submission/controller.py","/app/submission/design_report.json"})
            return Receipt(0,"created","")
        if command=="VERIFY_WORK": return Receipt(0,"verified","")
        for p in ("/app/submission/controller.py","/app/submission/design_report.json"):
            if p in command:
                return Receipt(0,"ok","") if p in self.files else Receipt(1,"","missing")
        return Receipt(0,"ok","")

def install(outputs):
    it=iter(outputs)
    planner.plan=lambda prompt,timeout_s=180: {"text":json.dumps(next(it)),"model":"independent-controlled"}
    planner.extract_json_object=lambda text: json.loads(text)
    planner.normalize_proposal_object=lambda obj: obj

async def cases():
    goal="Create /app/submission/controller.py and /app/submission/design_report.json for the task."

    install([{
      "material_requirements":["R1","BRAIN_DELIVERABLE_01","BRAIN_DELIVERABLE_02"],
      "candidates":[{"action_id":"make","covers":["R1","BRAIN_DELIVERABLE_01","BRAIN_DELIVERABLE_02"],"command":"CREATE_BOTH","verify_command":"VERIFY_WORK"}]
    }])
    out=await candidate.run_science_goal(goal,Env(),max_cycles=1)
    assert out["status"]=="SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER",out
    assert out["task_completion_claimed"] is False,out
    assert out["finish_authority"]=="RAW_TASK_ACCEPTANCE_V1_REQUIRED",out
    assert out["raw_task_acceptance_receipts_present"] is False,out
    assert out["raw_task_required_obligation_count"]==1,out
    assert out["raw_task_semantic_residual_obligation_count"]==1,out
    assert out["resolved_requirements"]==["BRAIN_DELIVERABLE_01","BRAIN_DELIVERABLE_02","R1"],out

    install([{"material_requirements":["R1"],"finish_summary":"pretend complete"}])
    out2=await candidate.run_science_goal(goal,Env(),max_cycles=1)
    assert out2["status"]!="FINISHED",out2
    assert out2.get("task_completion_claimed") is False,out2

    assert candidate._action_transport_clean(0,"","bash: warning: here-document at line 1") is False

asyncio.run(cases())
print(json.dumps({
 "status":"PASS",
 "exact_git_blob_sha":blob,
 "checks":[
   "EXACT_CURRENT_AGENT_BYTES_BOUND",
   "DECLARED_OUTPUTS_REQUIRED",
   "SUBMISSION_READY_NEVER_EQUALS_TASK_ACCEPTED",
   "RAW_TASK_ACCEPTANCE_RECEIPT_REMAINS_REQUIRED",
   "TRANSPORT_TRUNCATION_FAILS_CLOSED"
 ],
 "benchmark_task_exposure":0,
 "incremental_spend_usd":0
},sort_keys=True))
