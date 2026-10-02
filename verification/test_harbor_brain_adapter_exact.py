import asyncio
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

# Supply only the three astra_runtime helper contracts used by the exact adapter.
stub=types.ModuleType("canonical.runtime.astra_runtime")
stub._pack_observations_for_model=lambda observations,max_chars=12000: json.dumps(observations)[-max_chars:]
planner_queue=[]
def _planner_post(prompt,timeout_s=20):
    item=planner_queue.pop(0)
    return {"text":json.dumps(item),"model":"synthetic-zero-case"}
stub._planner_post=_planner_post
stub._extract_json_object=lambda text: json.loads(text)
sys.modules["canonical.runtime.astra_runtime"]=stub
import canonical.runtime
canonical.runtime.astra_runtime=stub

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

agent=load("brain_harbor_agent_exact","verification/harbor_brain_agent_exact.py")
transport=load("brain_harbor_transport_exact","verification/harbor_environment_transport_exact.py")

class FakeEnv:
    def __init__(self): self.commands=[]
    async def exec(self,command,timeout_sec=None,**kwargs):
        self.commands.append((command,timeout_sec,kwargs))
        if command=="printf hello":
            return SimpleNamespace(returncode=0,stdout="hello",stderr="")
        if "read_bytes" in command:
            return SimpleNamespace(returncode=0,stdout="fixture",stderr="")
        return SimpleNamespace(return_code=0,stdout="ok",stderr="")

class AdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_harbor_interface_and_guards(self):
        self.assertEqual(agent.HarborBrainAgent.name(),"project-brain")
        self.assertEqual(agent.SCHEMA,"PROJECT_BRAIN_HARBOR_AGENT_TRACE_V1")
        for cmd in [
            "curl https://example.invalid/x",
            "wget https://example.invalid/x",
            "git clone https://example.invalid/a.git",
            "pip install x",
            "apt-get install jq",
        ]:
            with self.assertRaises(ValueError):
                agent.validate_environment_command(cmd)
        self.assertEqual(agent.validate_environment_command("python -m unittest -q"),"python -m unittest -q")

    async def test_bounded_exec_then_finish(self):
        env=FakeEnv()
        planner_queue[:] = [
            {"actions":[{"type":"environment_exec","args":{"command":"pwd","timeout_s":9},"why":"synthetic"}]},
            {"actions":[{"type":"finish","args":{"summary":"done"},"why":"complete"}]},
        ]
        out=await agent.run_bounded_harbor_goal("synthetic adapter preflight",env,max_cycles=3)
        self.assertEqual(out["status"],"FINISHED")
        self.assertEqual(out["model_dependency_count"],1)
        self.assertEqual(env.commands[0][0],"pwd")
        self.assertEqual(env.commands[0][1],9)
        self.assertEqual(len(out["trace"]),1)

    async def test_non_allowlisted_action_fails_closed(self):
        env=FakeEnv()
        planner_queue[:] = [{"actions":[{"type":"http_get","args":{"url":"https://example.invalid"}}]}]
        with self.assertRaises(RuntimeError):
            await agent.run_bounded_harbor_goal("synthetic",env,max_cycles=1)

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_exec_receipt_and_predeclared_actions(self):
        env=FakeEnv()
        t=transport.HarborEnvironmentTransport(env)
        r=await t.exec("printf hello",timeout_sec=7)
        self.assertEqual((r.returncode,r.stdout),(0,"hello"))
        rr=await transport.execute_predeclared_action(t,{"type":"terminal_read_text","args":{"path":"/tmp/x"}})
        self.assertEqual(rr["text"],"fixture")
        ww=await transport.execute_predeclared_action(t,{"type":"terminal_write_text","args":{"path":"/tmp/x","text":"abc"}})
        self.assertEqual(ww["returncode"],0)
        with self.assertRaises(transport.HarborTransportError):
            await transport.execute_predeclared_action(t,{"type":"shell","args":{"command":"id"}})

    async def test_path_and_timeout_guards(self):
        t=transport.HarborEnvironmentTransport(FakeEnv())
        with self.assertRaises(transport.HarborTransportError):
            await t.read_text("../secret")
        with self.assertRaises(transport.HarborTransportError):
            await t.exec("id",timeout_sec=0)

if __name__=="__main__":
    unittest.main(verbosity=2)
