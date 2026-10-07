from __future__ import annotations
import asyncio, hashlib, importlib.util, json, pathlib, sys, types

ROOT = pathlib.Path(__file__).resolve().parent
TARGET = ROOT / "harbor_science_agent_v1.py"
EXPECTED_BLOB = "39cc756bafba817dfd697e65769da5ca0a316837"

raw = TARGET.read_bytes()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
assert blob == EXPECTED_BLOB, (blob, EXPECTED_BLOB)
compile(raw, str(TARGET), "exec")

canonical = types.ModuleType("canonical"); canonical.__path__ = []
runtime = types.ModuleType("canonical.runtime"); runtime.__path__ = []
planner = types.ModuleType("canonical.runtime.harbor_science_planner_v1")
policy = types.ModuleType("canonical.runtime.harbor_command_policy")
transport = types.ModuleType("canonical.runtime.harbor_environment_transport")

policy.validate_environment_command = lambda command: str(command)

class HarborEnvironmentTransport:
    def __init__(self, environment): self.environment = environment
    async def exec(self, command, timeout_sec=None):
        return await self.environment.exec(command, timeout_sec=timeout_sec)
transport.HarborEnvironmentTransport = HarborEnvironmentTransport

sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime
sys.modules["canonical.runtime.harbor_science_planner_v1"] = planner
sys.modules["canonical.runtime.harbor_command_policy"] = policy
sys.modules["canonical.runtime.harbor_environment_transport"] = transport
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
        self.output_exists=False
        self.commands=[]
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
        return {"text": json.dumps(next(it)), "model":"independent-synthetic"}
    planner.plan=plan
    planner.extract_json_object=lambda text: json.loads(text)
    planner.normalize_proposal_object=lambda obj: obj

async def cases():
    goal="Read /app/spec/config.txt and create /app/submission/result.json"

    # Exact declared source bytes are read before planning and mandatory output is frozen.
    env=Env()
    install([{"material_requirements":["R1"],"finish_summary":"pretend-done"}])
    out=await candidate.run_science_goal(goal,env,max_cycles=1)
    assert out["status"] != "FINISHED"
    assert out["brain_mandated_deliverables"] == {"BRAIN_DELIVERABLE_01":"/app/submission/result.json"}
    assert "BRAIN_DELIVERABLE_01" in out["material_requirements"]
    assert any("test -f /app/spec/config.txt" in c for c in env.commands)

    # Planner-declared completion cannot bypass absent output.
    failures=await candidate._declared_output_gate(env,["/app/submission/result.json"])
    assert failures and failures[0]["path"]=="/app/submission/result.json"

    # A candidate that creates the exact output, verifies, and passes Brain's independent
    # deliverable gate may finish. No planner-only coverage shortcut is enough.
    env=Env()
    install([{
        "material_requirements":["R1"],
        "candidates":[{
            "action_id":"a",
            "covers":["R1","BRAIN_DELIVERABLE_01"],
            "command":"CREATE_OUTPUT",
            "verify_command":"VERIFY_WORK"
        }]
    }])
    out=await candidate.run_science_goal(goal,env,max_cycles=1)
    assert out["status"]=="FINISHED", out
    assert out["finish_authority"]=="BRAIN_VERIFIED_STATE"
    assert set(out["resolved_requirements"])=={"R1","BRAIN_DELIVERABLE_01"}
    action=[x for x in out["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
    assert action["coverage_promoted"] is True
    assert action["brain_deliverable_checks"][0]["verified"] is True

    # Transport anomalies remain fail-closed.
    assert candidate._action_transport_clean(0,"","bash: warning: here-document at line 1") is False

asyncio.run(cases())
print(json.dumps({"status":"PASS","exact_git_blob_sha":blob,"cases":4},sort_keys=True))
