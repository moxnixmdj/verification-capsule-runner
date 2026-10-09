from __future__ import annotations

import unittest

from execution_guard import terminal_execution_admission_v2 as guard


STATIC_PREFIX = """\
persist-credentials: false
rm -rf llama.cpp
git init llama.cpp
cmake -S llama.cpp -B llama.cpp/build
cmake --build llama.cpp/build
http://127.0.0.1:8080/health
SYNTHETIC_COMPLETION.json
"""


def behavior(version: int) -> dict:
    return {
        "runtime_bindings": {
            "start_cas": {"path": f"capsules/rank15_start_cas_v{version}.py"},
            "prestart_guard": {"path": "capsules/rank15_prestart_token_guard_v3.py"},
            "finalizer": {"path": f"capsules/rank15_finalize_receipt_v{version}.py"},
            "agent": {"path": "capsules/canonical/runtime/harbor_science_agent_v3.py"},
        }
    }


def workflow(version: int) -> str:
    return STATIC_PREFIX + f"""\
rank15_start_cas_v{version}.py --check-absent
rank15_prestart_token_guard_v3.py
rank15_start_cas_v{version}.py --acquire
canonical.runtime.harbor_science_agent_v3:HarborScienceAgent
harbor run
rank15_finalize_receipt_v{version}.py
"""


class AdmissionV2RuntimeDerivedWorkflowTests(unittest.TestCase):
    def test_v3_bound_workflow_passes(self):
        self.assertEqual(guard.check_workflow(workflow(3), behavior(3)), [])

    def test_v4_bound_workflow_passes_without_guard_source_edit(self):
        self.assertEqual(guard.check_workflow(workflow(4), behavior(4)), [])

    def test_behavior_workflow_version_mismatch_fails_closed(self):
        errors = guard.check_workflow(workflow(4), behavior(3))
        self.assertTrue(
            any(x.startswith("WORKFLOW_REQUIRED_MARKER_MISSING:rank15_start_cas_v3.py") for x in errors),
            errors,
        )

    def test_phase_reordering_fails_closed(self):
        text = workflow(4).replace(
            "rank15_start_cas_v4.py --check-absent\nrank15_prestart_token_guard_v3.py",
            "rank15_prestart_token_guard_v3.py\nrank15_start_cas_v4.py --check-absent",
        )
        errors = guard.check_workflow(text, behavior(4))
        self.assertIn("WORKFLOW_PHASE_ORDER_INVALID", errors)

    def test_v2_regression_is_forbidden_even_if_other_markers_exist(self):
        text = workflow(4) + "rank15_finalize_receipt_v2.py\n"
        errors = guard.check_workflow(text, behavior(4))
        self.assertIn("WORKFLOW_FORBIDDEN:V2_FINALIZER", errors)

    def test_missing_runtime_binding_fails_closed(self):
        bad = behavior(4)
        del bad["runtime_bindings"]["start_cas"]
        errors = guard.check_workflow(workflow(4), bad)
        self.assertTrue(any("BEHAVIOR_RUNTIME_BINDING_MISSING:start_cas" in x for x in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
