from __future__ import annotations
import asyncio, hashlib, importlib.util, json, pathlib, sys, types
from dataclasses import dataclass

ROOT=pathlib.Path(__file__).resolve().parent
TARGET=ROOT/"harbor_science_agent_v1.py"
RAWROOT=ROOT.parent/"tb_science_current_raw_task_v1/canonical/runtime"
RAW_CONTRACT=RAWROOT/"lossless_raw_task_contract_v1.py"
RAW_LOCALIZER=RAWROOT/"raw_task_acceptance_residual_localizer_v1.py"
EXPECTED={
 "agent":"5bc8ebac26bb7c809d4698f535eff43b667b30df",
 "contract":"d54d5a2f7efa76b653d288f4f53da4883644baa6",
 "localizer":"f29616cf7726959aa28db4ed6541a9fc0bc2ac76",
}

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

assert blob(TARGET)==EXPECTED["agent"],(blob(TARGET),EXPECTED["agent"])
assert blob(RAW_CONTRACT)==EXPECTED["contract"],(blob(RAW_CONTRACT),EXPECTED["contract"])
assert blob(RAW_LOCALIZER)==EXPECTED["localizer"],(blob(RAW_LOCALIZER),EXPECTED["localizer"])

canonical=types.ModuleType("canonical"); canonical.__path__=[]
runtime=types.ModuleType("canonical.runtime"); runtime.__path__=[]
explicit=types.ModuleType("canonical.runtime.explicit_requirement_index_v2")
constraints=types.ModuleType("canonical.runtime.instruction_constraint_compiler_v1")
sourceprog=types.ModuleType("canonical.runtime.source_aligned_acceptance_program_v1")
planner=types.ModuleType("canonical.runtime.harbor_science_planner_v1")
policy=types.ModuleType("canonical.runtime.harbor_command_policy")
transport=types.ModuleType("canonical.runtime.harbor_environment_transport")

explicit.build_index=lambda text,source_id=None: {"status":"PASS","modal_obligations":[],"imperative_directives":[]}

class ConstraintError(ValueError): pass
constraints.ConstraintError=ConstraintError
@dataclass
class C:
    exact_response: str|None=None
    prefix: str|None=None
    suffix: str|None=None
    min_words: int|None=None
    max_words: int|None=None
    min_unique_words: int|None=None
    exact_numbers: tuple=()
    lowercase_only: bool=False
    uppercase_only: bool=False
    required_literals: tuple=()
    forbidden_literals: tuple=()
constraints.compile_constraints=lambda text: C()
sourceprog.compile_program=lambda *args,**kwargs: {"status":"UNRESOLVED","reason":"CONTROLLED_STUB_NO_OBJECTIVE_ROUTE"}

policy.validate_environment_command=lambda command: str(command)
class HarborEnvironmentTransport:
    def __init__(self,environment): self.environment=environment
    async def exec(self,command,timeout_sec=None): return await self.environment.exec(command,timeout_sec=timeout_sec)
transport.HarborEnvironmentTransport=HarborEnvironmentTransport

sys.modules.update({
 "canonical":canonical,
 "canonical.runtime":runtime,
 "canonical.runtime.explicit_requirement_index_v2":explicit,
 "canonical.runtime.instruction_constraint_compiler_v1":constraints,
 "canonical.runtime.source_aligned_acceptance_program_v1":sourceprog,
 "canonical.runtime.harbor_science_planner_v1":planner,
 "canonical.runtime.harbor_command_policy":policy,
 "canonical.runtime.harbor_environment_transport":transport,
})

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

raw_contract=load("canonical.runtime.lossless_raw_task_contract_v1",RAW_CONTRACT)
raw_localizer=load("canonical.runtime.raw_task_acceptance_residual_localizer_v1",RAW_LOCALIZER)
runtime.harbor_science_planner_v1=planner
candidate=load("candidate",TARGET)

contract=raw_contract.compile_contract(
    "Create alpha.\nCreate beta.",
    source_id="INDEPENDENT_TEST",
    routing_target_effects=["SCIENCE_CANDIDATE_READY"],
)
assert contract["pass"] is True,contract
assert contract["nonwhitespace_source_coverage_complete"] is True,contract
assert len(contract["acceptance_contract"]["obligations"])==2,contract
assert all(x["acceptance_receipt_required"] is True for x in contract["acceptance_contract"]["obligations"])
localized=raw_localizer.localize(contract)
assert localized["pass"] is True,localized
assert localized["all_required_obligations_accounted_for"] is True,localized
assert localized["accounted_obligation_count"]==2,localized
assert localized["semantic_residual_obligation_count"]==2,localized
assert localized["acceptance_credit_authorized"] is False,localized

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
    assert out["raw_task_required_obligation_count"]>=1,out
    assert out["raw_task_semantic_residual_obligation_count"]>=1,out

    install([{"material_requirements":["R1"],"finish_summary":"pretend complete"}])
    out2=await candidate.run_science_goal(goal,Env(),max_cycles=1)
    assert out2["status"]!="FINISHED",out2
    assert out2.get("task_completion_claimed") is False,out2

    assert candidate._action_transport_clean(0,"","bash: warning: here-document at line 1") is False

asyncio.run(cases())
print(json.dumps({
 "status":"PASS",
 "exact_git_blob_shas":{k:blob(p) for k,p in {"agent":TARGET,"contract":RAW_CONTRACT,"localizer":RAW_LOCALIZER}.items()},
 "checks":[
   "EXACT_CURRENT_AGENT_BYTES_BOUND",
   "EXACT_RAW_TASK_COMPILER_BYTES_BOUND",
   "EXACT_RAW_TASK_LOCALIZER_BYTES_BOUND",
   "LOSSLESS_NONWHITESPACE_SCOPE_PRESERVED",
   "EVERY_RAW_OBLIGATION_ACCOUNTED",
   "SEMANTIC_RESIDUAL_NEVER_SILENTLY_ACCEPTED",
   "SUBMISSION_READY_NEVER_EQUALS_TASK_ACCEPTED",
   "TRANSPORT_TRUNCATION_FAILS_CLOSED"
 ],
 "benchmark_task_exposure":0,
 "incremental_spend_usd":0
},sort_keys=True))
