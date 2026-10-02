import asyncio, hashlib, json, sys, types
from types import SimpleNamespace

SOURCE = "\"\"\"Harbor adapter for the canonical Project Brain controller.\n\nThis module is transport glue, not a new controller. It reuses the bounded\nproposal/finalization helpers in canonical.runtime.astra_runtime and exposes only\nthe Harbor task environment as an action surface.\n\nTerminal capability credit MUST NOT come from this adapter itself. Every run\nrecords whether the controller was model-assisted; donor/dependency accounting\nremains authoritative.\n\"\"\"\nfrom __future__ import annotations\n\nimport json\nimport re\nfrom pathlib import Path\nfrom typing import Any\n\nfrom canonical.runtime import astra_runtime\n\ntry:\n    from harbor.agents.base import BaseAgent\n    from harbor.agents.capabilities import AgentCapabilities\n    from harbor.environments.base import BaseEnvironment\n    from harbor.models.agent.context import AgentContext\nexcept ImportError:  # lets Brain unit tests import without Harbor installed\n    BaseAgent = object  # type: ignore[assignment,misc]\n    BaseEnvironment = Any  # type: ignore[assignment,misc]\n    AgentContext = Any  # type: ignore[assignment,misc]\n\n    class AgentCapabilities:  # type: ignore[no-redef]\n        def __init__(self, **kwargs: Any) -> None:\n            self.kwargs = kwargs\n\n\nSCHEMA = \"PROJECT_BRAIN_HARBOR_AGENT_TRACE_V1\"\nMAX_CYCLES = 12\nMAX_COMMAND_CHARS = 12000\nMAX_OUTPUT_CHARS = 16000\n\n_FORBIDDEN_COMMAND_PATTERNS = (\n    r\"(?i)\\b(curl|wget)\\b\",\n    r\"(?i)\\bgit\\s+(clone|fetch|pull)\\b\",\n    r\"(?i)\\b(pip|pip3|uv|poetry)\\s+install\\b\",\n    r\"(?i)\\b(apt|apt-get|dnf|yum|apk)\\s+.*\\binstall\\b\",\n    r\"(?i)\\bssh\\b\",\n    r\"(?i)\\bscp\\b\",\n)\n\n\ndef validate_environment_command(command: Any) -> str:\n    if not isinstance(command, str) or not command.strip():\n        raise ValueError(\"HARBOR_COMMAND_REQUIRED\")\n    command = command.strip()\n    if len(command) > MAX_COMMAND_CHARS:\n        raise ValueError(\"HARBOR_COMMAND_TOO_LONG\")\n    if \"\\x00\" in command:\n        raise ValueError(\"HARBOR_COMMAND_NUL\")\n    for pattern in _FORBIDDEN_COMMAND_PATTERNS:\n        if re.search(pattern, command):\n            raise ValueError(\"HARBOR_COMMAND_EXTERNAL_ACQUISITION_FORBIDDEN\")\n    return command\n\n\ndef _planner_action(raw: dict[str, Any]) -> dict[str, Any]:\n    action = raw.get(\"action\")\n    if not isinstance(action, dict):\n        actions = raw.get(\"actions\")\n        if isinstance(actions, list) and actions and isinstance(actions[0], dict):\n            action = actions[0]\n    if not isinstance(action, dict) and isinstance(raw.get(\"next_action\"), dict):\n        action = raw[\"next_action\"]\n    if not isinstance(action, dict):\n        raise RuntimeError(\"HARBOR_PLANNER_ACTION_MISSING\")\n    typ = action.get(\"type\")\n    if isinstance(typ, str) and \".\" in typ:\n        typ = typ.rsplit(\".\", 1)[-1]\n        action = dict(action)\n        action[\"type\"] = typ\n    if typ not in {\"environment_exec\", \"finish\"}:\n        raise RuntimeError(\"HARBOR_PLANNER_ACTION_REJECTED:\" + str(typ))\n    if not isinstance(action.get(\"args\"), dict):\n        raise RuntimeError(\"HARBOR_PLANNER_ARGS_INVALID\")\n    return action\n\n\nasync def run_bounded_harbor_goal(\n    goal: str,\n    environment: BaseEnvironment,\n    *,\n    max_cycles: int = 8,\n) -> dict[str, Any]:\n    goal = str(goal or \"\").strip()\n    if not goal:\n        raise ValueError(\"HARBOR_GOAL_REQUIRED\")\n    max_cycles = max(1, min(int(max_cycles), MAX_CYCLES))\n    observations: list[dict[str, Any]] = []\n    trace: list[dict[str, Any]] = []\n\n    for cycle in range(max_cycles):\n        obs = astra_runtime._pack_observations_for_model(observations, max_chars=12000)\n        prompt = (\n            \"You are an OPTIONAL proposal source inside Project Brain, not the authority. \"\n            \"Return JSON text only. The task environment is isolated and terminal evidence \"\n            \"must not be used to discover new external solutions. \"\n            \"Goal: \" + goal + \"\\n\"\n            \"Allowed actions: environment_exec(command, timeout_s), finish(summary). \"\n            \"environment_exec may inspect or modify ONLY the supplied task environment. \"\n            \"No network acquisition, no package installation, no git fetch/clone/pull, \"\n            \"no secrets. Prefer the smallest falsifiable action. \"\n            \"Schema: {\\\"actions\\\":[{\\\"type\\\":\\\"...\\\",\\\"args\\\":{},\\\"why\\\":\\\"...\\\"}]}. \"\n            \"Observations envelope: \" + obs\n        )\n        planned = astra_runtime._planner_post(prompt, timeout_s=20)\n        raw = astra_runtime._extract_json_object(planned.get(\"text\", \"\"))\n        action = _planner_action(raw)\n        typ = action[\"type\"]\n\n        if typ == \"finish\":\n            summary = str(action[\"args\"].get(\"summary\") or \"\").strip()\n            if not summary:\n                raise RuntimeError(\"HARBOR_EMPTY_FINISH\")\n            return {\n                \"schema\": SCHEMA,\n                \"status\": \"FINISHED\",\n                \"controller_mode\": \"OPTIONAL_MODEL_ADVISORY\",\n                \"model_dependency_count\": 1,\n                \"planner_model_last\": planned.get(\"model\"),\n                \"cycles\": cycle + 1,\n                \"trace\": trace,\n                \"summary\": summary,\n            }\n\n        command = validate_environment_command(action[\"args\"].get(\"command\"))\n        raw_timeout = action[\"args\"].get(\"timeout_s\", 60)\n        try:\n            timeout_s = max(1, min(int(raw_timeout), 180))\n        except (TypeError, ValueError):\n            raise RuntimeError(\"HARBOR_TIMEOUT_INVALID\")\n        result = await environment.exec(command=command, timeout_sec=timeout_s)\n        stdout = str(getattr(result, \"stdout\", \"\") or \"\")[-MAX_OUTPUT_CHARS:]\n        stderr = str(getattr(result, \"stderr\", \"\") or \"\")[-MAX_OUTPUT_CHARS:]\n        returncode = int(getattr(result, \"return_code\", getattr(result, \"returncode\", 0)) or 0)\n        observed = {\n            \"returncode\": returncode,\n            \"stdout\": stdout,\n            \"stderr\": stderr,\n        }\n        trace.append({\n            \"cycle\": cycle,\n            \"action\": {\"type\": typ, \"args\": {\"command\": command, \"timeout_s\": timeout_s}},\n            \"result\": observed,\n        })\n        observations.append({\"action\": action, \"result\": observed})\n\n    final_obs = astra_runtime._pack_observations_for_model(observations, max_chars=12000)\n    final_prompt = (\n        \"FINALIZATION ONLY. Do not request tools. Return JSON text only with \"\n        \"{\\\"summary\\\":\\\"...\\\"}. Goal: \" + goal +\n        \"\\nAdmitted observations: \" + final_obs\n    )\n    finalized = astra_runtime._planner_post(final_prompt, timeout_s=20)\n    obj = astra_runtime._extract_json_object(finalized.get(\"text\", \"\"))\n    summary = obj.get(\"summary\")\n    if not isinstance(summary, str) or not summary.strip():\n        raise RuntimeError(\"HARBOR_FINALIZATION_INVALID\")\n    return {\n        \"schema\": SCHEMA,\n        \"status\": \"FINISHED_AFTER_BOUNDED_ACTIONS\",\n        \"controller_mode\": \"OPTIONAL_MODEL_ADVISORY_FORCED_FINALIZATION\",\n        \"model_dependency_count\": 1,\n        \"planner_model_last\": finalized.get(\"model\"),\n        \"cycles\": max_cycles,\n        \"trace\": trace,\n        \"summary\": summary.strip(),\n    }\n\n\nclass HarborBrainAgent(BaseAgent):  # type: ignore[misc]\n    \"\"\"Harbor custom agent that binds a task environment to Project Brain.\"\"\"\n\n    capabilities = AgentCapabilities()\n\n    @staticmethod\n    def name() -> str:\n        return \"project-brain\"\n\n    def version(self) -> str:\n        return \"1.0.0\"\n\n    async def setup(self, environment: BaseEnvironment) -> None:\n        return None\n\n    async def run(\n        self,\n        instruction: str,\n        environment: BaseEnvironment,\n        context: AgentContext,\n    ) -> None:\n        result = await run_bounded_harbor_goal(instruction, environment)\n        self.logs_dir.mkdir(parents=True, exist_ok=True)\n        trace_path = self.logs_dir / \"project_brain_harbor_trace.json\"\n        trace_path.write_text(json.dumps(result, indent=2, sort_keys=True) + \"\\n\", encoding=\"utf-8\")\n        if hasattr(context, \"cost_usd\"):\n            context.cost_usd = 0.0\n"
EXPECTED_GIT_BLOB = "2de1d66d6c99636b72fe16e624044d1f7c464468"

def git_blob_sha(text):
    raw=text.encode("utf-8")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

assert git_blob_sha(SOURCE)==EXPECTED_GIT_BLOB, (git_blob_sha(SOURCE), EXPECTED_GIT_BLOB)

# Stub exact imported boundaries so the Brain adapter blob is exercised without
# needing access to the private Brain repository or any opaque model.
canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
astra=types.ModuleType("canonical.runtime.astra_runtime")
def pack(obs,max_chars=12000): return json.dumps({"observations":obs},sort_keys=True)
astra._pack_observations_for_model=pack
astra._planner_post=lambda prompt,timeout_s=20: {"text":"stub","model":"public-verifier-stub"}
canonical.runtime=runtime
runtime.astra_runtime=astra
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime
sys.modules["canonical.runtime.astra_runtime"]=astra

harbor=types.ModuleType("harbor")
agents=types.ModuleType("harbor.agents")
base=types.ModuleType("harbor.agents.base")
caps=types.ModuleType("harbor.agents.capabilities")
envs=types.ModuleType("harbor.environments")
envbase=types.ModuleType("harbor.environments.base")
models=types.ModuleType("harbor.models")
agentmods=types.ModuleType("harbor.models.agent")
ctxmod=types.ModuleType("harbor.models.agent.context")
class BaseAgent: pass
class AgentCapabilities:
    def __init__(self,**kwargs): self.kwargs=kwargs
class BaseEnvironment: pass
class AgentContext:
    def __init__(self): self.cost_usd=None
base.BaseAgent=BaseAgent
caps.AgentCapabilities=AgentCapabilities
envbase.BaseEnvironment=BaseEnvironment
ctxmod.AgentContext=AgentContext
for name,mod in {
 "harbor":harbor,"harbor.agents":agents,"harbor.agents.base":base,
 "harbor.agents.capabilities":caps,"harbor.environments":envs,
 "harbor.environments.base":envbase,"harbor.models":models,
 "harbor.models.agent":agentmods,"harbor.models.agent.context":ctxmod,
}.items(): sys.modules[name]=mod

ns={"__name__":"brain_harbor_exact_blob"}
exec(compile(SOURCE,"harbor_brain_agent.py","exec"),ns)

validate=ns["validate_environment_command"]
run_goal=ns["run_bounded_harbor_goal"]
planner_action=ns["_planner_action"]

for bad in [
 "curl https://example.com/x","wget https://example.com/x",
 "git clone https://example.com/a.git","pip install foo","apt-get install jq","ssh host"
]:
    try: validate(bad)
    except ValueError: pass
    else: raise AssertionError("external acquisition command admitted: "+bad)
assert validate("python -m unittest -q")=="python -m unittest -q"

try: planner_action({"actions":[{"type":"http_get","args":{"url":"https://x"}}]})
except RuntimeError: pass
else: raise AssertionError("non-allowlisted action admitted")

class FakeEnv:
    def __init__(self): self.commands=[]
    async def exec(self,command,timeout_sec=None):
        self.commands.append((command,timeout_sec))
        return SimpleNamespace(return_code=0,stdout="ok\n",stderr="")

async def main():
    env=FakeEnv()
    seq=iter([
      {"actions":[{"type":"environment_exec","args":{"command":"pwd","timeout_s":12},"why":"inspect"}]},
      {"actions":[{"type":"finish","args":{"summary":"done"},"why":"finish"}]},
    ])
    astra._extract_json_object=lambda text: next(seq)
    out=await run_goal("inspect task",env,max_cycles=3)
    assert out["status"]=="FINISHED"
    assert out["model_dependency_count"]==1
    assert env.commands==[("pwd",12)]
    assert len(out["trace"])==1
    print(json.dumps({
      "status":"INDEPENDENT_PASS",
      "brain_git_blob":EXPECTED_GIT_BLOB,
      "verified":[
        "EXACT_BLOB_EXECUTED",
        "LOCAL_TASK_ENV_ACTION_ALLOWED",
        "EXTERNAL_ACQUISITION_BLOCKED",
        "NON_ALLOWLISTED_PLANNER_ACTION_BLOCKED",
        "MODEL_DEPENDENCE_RECORDED",
        "COMMAND_RESULT_TRACE_RECORDED"
      ]
    },sort_keys=True))

asyncio.run(main())
