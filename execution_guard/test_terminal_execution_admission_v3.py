from __future__ import annotations

import unittest
from execution_guard import terminal_execution_admission_v3 as guard

STATIC = """\
persist-credentials: false
rm -rf llama.cpp
git init llama.cpp
cmake -S llama.cpp -B llama.cpp/build
cmake --build llama.cpp/build
http://127.0.0.1:8080/health
SYNTHETIC_COMPLETION.json
"""

def direct_behavior() -> dict:
    return {
        "behavior": {"agent_ready_precedes_start_cas": False},
        "runtime_bindings": {
            "start_cas": {"path": "capsules/rank15_start_cas_v4.py"},
            "prestart_guard": {"path": "capsules/rank15_prestart_token_guard_v3.py"},
            "finalizer": {"path": "capsules/rank15_finalize_receipt_v4.py"},
            "agent": {"path": "capsules/canonical/runtime/harbor_science_agent_v3.py"},
        },
    }

def delegated_behavior() -> dict:
    return {
        "behavior": {"agent_ready_precedes_start_cas": True},
        "runtime_bindings": {
            "start_cas": {"path": "capsules/rank15_start_cas_v6.py"},
            "prestart_guard": {"path": "capsules/rank15_prestart_token_guard_v4.py"},
            "finalizer": {"path": "capsules/rank15_finalize_receipt_v6.py"},
            "agent": {"path": "capsules/canonical/runtime/harbor_science_agent_v8.py"},
            "status_journal_runner": {"path": "capsules/rank15_v6_status_journal_runner.py"},
        },
    }

def direct_workflow() -> str:
    return STATIC + """\
rank15_start_cas_v4.py --check-absent
rank15_prestart_token_guard_v3.py
rank15_start_cas_v4.py --acquire
canonical.runtime.harbor_science_agent_v3:HarborScienceAgent
harbor run
rank15_finalize_receipt_v4.py
"""

def delegated_workflow() -> str:
    return STATIC + """\
python "$C/rank15_start_cas_v6.py" --check-absent
python "$C/rank15_prestart_token_guard_v4.py"
python "$C/rank15_v6_status_journal_runner.py"
python "$C/rank15_finalize_receipt_v6.py"
"""

class AdmissionV3Tests(unittest.TestCase):
    def test_legacy_direct_route_still_passes(self):
        self.assertEqual(guard.check_workflow(direct_workflow(), direct_behavior()), [])

    def test_delegated_barrier_route_passes_without_fake_harbor_markers(self):
        self.assertEqual(guard.check_workflow(delegated_workflow(), delegated_behavior()), [])

    def test_delegated_route_rejects_direct_start_bypass(self):
        text=delegated_workflow().replace(
            "rank15_v6_status_journal_runner.py",
            "rank15_start_cas_v6.py --acquire\nrank15_v6_status_journal_runner.py",
        )
        errors=guard.check_workflow(text, delegated_behavior())
        self.assertIn("WORKFLOW_DELEGATION_BYPASS:DIRECT_START_ACQUIRE", errors)

    def test_delegated_route_rejects_direct_harbor_bypass(self):
        text=delegated_workflow().replace(
            "rank15_v6_status_journal_runner.py",
            "harbor run\nrank15_v6_status_journal_runner.py",
        )
        errors=guard.check_workflow(text, delegated_behavior())
        self.assertIn("WORKFLOW_DELEGATION_BYPASS:DIRECT_HARBOR_RUN", errors)

    def test_phase_reordering_fails_closed(self):
        lines = delegated_workflow().splitlines()
        start_i = next(i for i, line in enumerate(lines) if "rank15_start_cas_v6.py" in line and "--check-absent" in line)
        prestart_i = next(i for i, line in enumerate(lines) if "rank15_prestart_token_guard_v4.py" in line)
        lines[start_i], lines[prestart_i] = lines[prestart_i], lines[start_i]
        text = "\n".join(lines) + "\n"
        self.assertIn("WORKFLOW_PHASE_ORDER_INVALID", guard.check_workflow(text, delegated_behavior()))

    def test_contents_write_is_forbidden(self):
        errors=guard.check_workflow(delegated_workflow()+"\ncontents: write\n", delegated_behavior())
        self.assertIn("WORKFLOW_FORBIDDEN:CONTENTS_WRITE_AUTHORITY", errors)

if __name__ == "__main__":
    unittest.main(verbosity=2)
