from __future__ import annotations
import asyncio, hashlib, importlib.util, json, pathlib, sys, types

ROOT = pathlib.Path(__file__).resolve().parent
TARGET = ROOT / "harbor_science_agent_v1.py"
EXPECTED_BLOB = "5bc8ebac26bb7c809d4698f535eff43b667b30df"

raw = TARGET.read_bytes()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
assert blob == EXPECTED_BLOB, (blob, EXPECTED_BLOB)
compile(raw, str(TARGET), "exec")

canonical = types.ModuleType("canonical"); canonical.__path__ = []
runtime = types.ModuleType("canonical.runtime"); runtime.__path__ = []
planner = types.ModuleType("canonical.runtime.harbor_science_planner_v1")
policy = types.ModuleType("canonical.runtime.harbor_command_policy")
transport = types.ModuleType("canonical.runtime.harbor_environment_transport")
lossless = types.ModuleType("canonical.runtime.lossless_raw_task_contract_v1")
localizer = types.ModuleType("canonical.runtime.raw_task_acceptance_residual_localizer_v1")

policy.validate_environment_command = lambda command: str(command)

class HarborEnvironmentTransport:
    def __init__(self, environment): self.environment = environment
    async def exec(self, command, timeout_sec=None):
        return await self.environment.exec(command, timeout_sec=timeout_sec)
transport.HarborEnvironmentTransport = HarborEnvironmentTransport

def compile_contract(goal, source_id=None, routing_target_effects=None):
    seg = str(goal)
    sid = hashlib.sha256(seg.encode()).hexdigest()
    material = {"goal":seg,"source_id":source_id,"routing_target_effects":routing_target_effects}
    return {
        "pass": True,
        "task_contract_sha256": hashlib.sha256(json.dumps(material,sort_keys=True).encode()).hexdigest(),
        "acceptance_contract": {
            "required_obligation_ids":["O1"],
            "obligations":[{"obligation_id":"O1","segment_sha256":sid,"text":seg}],
        },
    }
lossless.compile_contract = compile_contract

def localize(contract):
    rows=contract["acceptance_contract"]["obligations"]
    return {
        "pass": True,
        "accounted_obligation_count": len(rows),
        "objective_route_obligation_count": len(rows),
        "semantic_residual_obligation_count": 0,
        "obligations":[{"obligation_id":r["obligation_id"],"status":"ACCEPTANCE_PENDING"} for r in rows],
    }
localizer.localize = localize

sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime
sys.modules["canonical.runtime.harbor_science_planner_v1"] = planner
sys.modules["canonical.runtime.harbor_command_policy"] = policy
sys.modules["canonical.runtime.harbor_environment_transport"] = transport
sys.modules["canonical.runtime.lossless_raw_task_contract_v1"] = lossless
sys.modules["canonical.runtime.raw_task_acceptance_residual_localizer_v1"] = localizer
runtime.harbor_science_planner_v1 = planner

spec = importlib.util.spec_from_file_location("candidate", TARGET)
candidate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate)

class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

class Env:
    def __init__(self):
        self.output_exists=False; self.commands=[]
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command.startswith("test -f /app/spec/config.txt"):
            return Receipt(0, "abc123  /app/spec/config.txt\n---CONTENT---\nGAIN=7\n", "")
        if command == "CREATE_OUTPUT":
            self.output_exists=True
            return Receipt(0, "created", "")
        if "/app/submission/result.json" in command:
            return Receipt(0 if self.output_exists else 1, "ok" if self.output_exists else "", "" if self.output_exists else "missing")
        if command == "VERIFY_WORK":
            return Receipt(0, "verified", "")
        return Receipt(0, "ok", "")

def install(outputs):
    it=iter(outputs)
    def plan(prompt, timeout_s=180):
        return {"text":json.dumps(next(it)),"model":"independent-synthetic"}
    planner.plan=plan
    planner.extract_json_object=lambda text: json.loads(text)
    planner.normalize_proposal_object=lambda obj: obj

async def cases():
    goal="Treat /app/spec/config.txt as authoritative. Create /app/submission/result.json."

    # Exact declared input is snapshotted and the explicit output becomes Brain-mandated.
    env=Env()
    install([
      {"material_requirements":["R1"],"candidates":[{"action_id":"a","covers":["R1","BRAIN_DELIVERABLE_01"],"command":"CREATE_OUTPUT","verify_command":"VERIFY_WORK"}]},
      {"finish_summary":"candidate done"}
    ])
    out=await candidate.run_science_goal(goal,env,max_cycles=2)
    assert any(c.startswith("test -f /app/spec/config.txt") for c in env.commands), env.commands
    assert out["brain_mandated_deliverables"]=={"BRAIN_DELIVERABLE_01":"/app/submission/result.json"}, out
    assert set(out["resolved_requirements"])=={"R1","BRAIN_DELIVERABLE_01"}, out

    # Crucial new boundary: controller may only expose a submission-ready state.
    assert out["status"]=="SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER", out
    assert out["task_completion_claimed"] is False, out
    assert out["finish_authority"]=="RAW_TASK_ACCEPTANCE_V1_REQUIRED", out
    assert out["raw_task_acceptance_receipts_present"] is False, out
    assert out["raw_task_required_obligation_count"] >= 1, out

    # Missing explicit outputs remain fail-closed.
    missing=Env()
    failures=await candidate._declared_output_gate(missing,["/app/submission/result.json"])
    assert failures and failures[0]["path"]=="/app/submission/result.json"

    # Exact rank7 transport-laundering shape remains blocked.
    assert candidate._action_transport_clean(0,"","bash: warning: here-document at line 1") is False

    # Lossless raw-task scope remains non-droppable and acceptance-pending.
    contract,localized,rows=candidate._compile_lossless_task_scope("Create alpha. Create beta.")
    assert contract["pass"] is True
    assert localized["pass"] is True
    assert rows and all(r["acceptance_receipt_required"] for r in rows)

asyncio.run(cases())
print(json.dumps({
  "status":"PASS",
  "exact_git_blob_sha":blob,
  "cases":5,
  "benchmark_task_exposure":0,
  "terminal_credit":0
},sort_keys=True))
