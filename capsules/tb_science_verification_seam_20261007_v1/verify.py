from __future__ import annotations
import asyncio, hashlib, importlib.util, json, pathlib, sys, types

ROOT = pathlib.Path(__file__).resolve().parent
TARGET = ROOT / "harbor_science_agent_v1.py"
EXPECTED_BLOB = "7d54d67f7c4b62cd0c3477dc945bc7c2385b5289"

raw = TARGET.read_bytes()
git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()
assert git_blob == EXPECTED_BLOB, (git_blob, EXPECTED_BLOB)
compile(raw, str(TARGET), "exec")

canonical = types.ModuleType("canonical"); canonical.__path__ = []
runtime = types.ModuleType("canonical.runtime"); runtime.__path__ = []
planner = types.ModuleType("canonical.runtime.harbor_science_planner_v1")
policy = types.ModuleType("canonical.runtime.harbor_command_policy")
transport = types.ModuleType("canonical.runtime.harbor_environment_transport")

def validate_environment_command(command):
    assert isinstance(command, str) and command.strip()
    return command.strip()
policy.validate_environment_command = validate_environment_command

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
    def __init__(self): self.commands=[]
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command == "warn-action":
            return Receipt(0, "", "bash: line 22: warning: here-document at line 1 delimited by end-of-file")
        if command == "verify-bad":
            return Receipt(1, "", "bad")
        return Receipt(0, "ok", "")

def install_planner(outputs):
    it=iter(outputs)
    def plan(prompt, timeout_s=180):
        return {"text": json.dumps(next(it)), "model": "independent-synthetic"}
    planner.plan=plan
    planner.extract_json_object=lambda text: json.loads(text)
    planner.normalize_proposal_object=lambda obj: obj

assert candidate._verify_command_is_material("echo OK") is False
assert candidate._verify_command_is_material("printf ok") is False
assert candidate._verify_command_is_material("true") is False
assert candidate._verify_command_is_material("test -f /app/submission/controller.py") is True
assert candidate._output_has_fatal_marker({"stdout":"","stderr":"warning: here-document at line 1"}) is True

async def run_cases():
    env=Env()
    install_planner([
        {"material_requirements":["R1"],"candidates":[{"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"echo OK"}]},
        {"finish_summary":"premature"},
    ])
    r=await candidate.run_science_goal("g",env,max_cycles=2)
    assert r["status"] != "FINISHED"
    assert r["resolved_requirements"] == []
    a=[x for x in r["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
    assert a["verification_block_reason"] == "TRIVIAL_OR_NONOBSERVING_VERIFY_COMMAND"
    assert a["coverage_promoted"] is False

    env=Env()
    install_planner([
        {"material_requirements":["R1"],"candidates":[{"action_id":"a","covers":["R1"],"command":"warn-action","verify_command":"test -f /tmp/x"}]},
        {"finish_summary":"premature"},
    ])
    r=await candidate.run_science_goal("g",env,max_cycles=2)
    assert r["status"] != "FINISHED"
    assert r["resolved_requirements"] == []
    a=[x for x in r["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
    assert a["verification_block_reason"] == "ACTION_OUTPUT_ANOMALY"
    assert "test -f /tmp/x" not in env.commands

    env=Env()
    install_planner([
        {"material_requirements":["R1"],"candidates":[{"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"test -d /tmp"}]}
    ])
    r=await candidate.run_science_goal("g",env,max_cycles=1)
    assert r["status"] == "FINISHED"
    assert r["resolved_requirements"] == ["R1"]

asyncio.run(run_cases())
print(json.dumps({"status":"PASS","exact_git_blob_sha":git_blob,"cases":3},sort_keys=True))
