import importlib.util, os, pathlib, unittest
from unittest import mock

P=pathlib.Path(__file__).with_name("astra_runtime_terminal_guard.py")
spec=importlib.util.spec_from_file_location("guarded_runtime",P)
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

class TerminalLocalPlannerGuardTests(unittest.TestCase):
    def test_no_bridge_blocks_without_network_fallback(self):
        with mock.patch.dict(os.environ,{"PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY":"1","PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR":""},clear=False), \
             mock.patch.object(runtime,"_external_tool_bridge",return_value=None), \
             mock.patch.object(runtime.urllib.request,"urlopen",side_effect=AssertionError("network fallback forbidden")):
            with self.assertRaisesRegex(runtime.Blocker,"TERMINAL_LOCAL_PLANNER_BRIDGE_REQUIRED"):
                runtime._planner_post("terminal")

    def test_wrong_model_blocks(self):
        bad={"text":"{}","model":"openai-fast","backend":"REMOTE","duration_s":0,"errors":[]}
        with mock.patch.dict(os.environ,{"PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY":"1"},clear=False), \
             mock.patch.object(runtime,"_external_tool_bridge",return_value=bad):
            with self.assertRaisesRegex(runtime.Blocker,"TERMINAL_LOCAL_PLANNER_MODEL_IDENTITY_MISMATCH"):
                runtime._planner_post("terminal")

    def test_wrong_backend_blocks(self):
        bad={"text":"{}","model":"Qwen3.5-9B-M-Q4_K_M-local","backend":"REMOTE","duration_s":0,"errors":[]}
        with mock.patch.dict(os.environ,{"PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY":"1"},clear=False), \
             mock.patch.object(runtime,"_external_tool_bridge",return_value=bad):
            with self.assertRaisesRegex(runtime.Blocker,"TERMINAL_LOCAL_PLANNER_BACKEND_IDENTITY_MISMATCH"):
                runtime._planner_post("terminal")

    def test_exact_local_identity_passes(self):
        good={"text":"{}","model":"Qwen3.5-9B-M-Q4_K_M-local","backend":"LOCAL_LLAMA_SERVER","duration_s":0,"errors":[]}
        with mock.patch.dict(os.environ,{"PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY":"1"},clear=False), \
             mock.patch.object(runtime,"_external_tool_bridge",return_value=good):
            out=runtime._planner_post("terminal")
        self.assertEqual(out["model"],"Qwen3.5-9B-M-Q4_K_M-local")
        self.assertEqual(out["backend"],"LOCAL_LLAMA_SERVER")
        self.assertEqual(out["transport"],"EXTERNAL_TOOL_BRIDGE")

if __name__=="__main__":
    unittest.main(verbosity=2)
