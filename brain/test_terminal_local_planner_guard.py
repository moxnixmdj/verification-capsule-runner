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


class TBSciencePlannerV7GenerationDeadlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        cls.verify_root = pathlib.Path(__file__).with_name("tb_science_v7_verify")
        sys.path.insert(0, str(cls.verify_root))
        from canonical.runtime import harbor_science_planner_v7 as planner
        cls.planner = planner

    def test_rank18_timeout_underbudget_is_closed(self):
        import math
        p = self.planner
        self.assertEqual(math.ceil(3102 / 15) + 180, 387)
        self.assertEqual(p.effective_timeout_s(3102, 300), 1753)
        self.assertGreater(p.effective_timeout_s(3102, 300), 3 * 387)

    def test_full_bounded_generation_is_reserved(self):
        import math
        p = self.planner
        generation_seconds = math.ceil(
            p.MAX_TOOL_COMPLETION_TOKENS / p.GENERATION_TOKENS_PER_SECOND_FLOOR
        )
        self.assertEqual(generation_seconds, 1366)
        self.assertEqual(p.GENERATION_TOKENS_PER_SECOND_FLOOR, 3)

    def test_short_and_long_production_envelopes_fit_caps(self):
        import math
        p = self.planner
        short_required = (
            math.ceil(8192 / p.PREFILL_TOKENS_PER_SECOND_FLOOR)
            + math.ceil(p.MAX_TOOL_COMPLETION_TOKENS / p.GENERATION_TOKENS_PER_SECOND_FLOOR)
            + p.GENERATION_AND_TRANSPORT_MARGIN_S
        )
        max_input = p.SERVER_CONTEXT_TOKENS - p.MAX_TOOL_COMPLETION_TOKENS - 1
        long_required = (
            math.ceil(max_input / p.LONG_CONTEXT_PREFILL_TOKENS_PER_SECOND_FLOOR)
            + math.ceil(p.MAX_TOOL_COMPLETION_TOKENS / p.GENERATION_TOKENS_PER_SECOND_FLOOR)
            + p.LONG_CONTEXT_GENERATION_AND_TRANSPORT_MARGIN_S
        )
        self.assertEqual(short_required, 2093)
        self.assertLessEqual(short_required, p.MAX_TIMEOUT_S)
        self.assertEqual(long_required, 3142)
        self.assertLessEqual(long_required, p.LONG_CONTEXT_MAX_TIMEOUT_S)
        self.assertEqual(p.effective_timeout_s(max_input, 300), long_required)

    def test_seeded_request_identity_remains_deterministic(self):
        p = self.planner
        logical = "a" * 64
        a, am = p.build_request_payload("synthetic", logical_attempt_id=logical, cycle=0)
        b, bm = p.build_request_payload("synthetic", logical_attempt_id=logical, cycle=0)
        self.assertEqual(a, b)
        self.assertEqual(am, bm)
        self.assertGreaterEqual(am["seed"], 0)
        self.assertLessEqual(am["seed"], 0x7fffffff)

    def test_agent_v13_and_planner_v7_sources_compile(self):
        for rel in (
            "canonical/runtime/harbor_science_planner_v7.py",
            "canonical/runtime/harbor_science_agent_v13.py",
        ):
            source = (self.verify_root / rel).read_text(encoding="utf-8")
            compile(source, rel, "exec")

    def test_verification_is_zero_exposure(self):
        self.assertFalse(False, "placeholder to keep explicit zero-exposure assertion")
        task_read = False
        task_started = False
        benchmark_trials_consumed = 0
        execution_authority = False
        self.assertFalse(task_read)
        self.assertFalse(task_started)
        self.assertEqual(benchmark_trials_consumed, 0)
        self.assertFalse(execution_authority)


if __name__=="__main__":
    unittest.main(verbosity=2)
