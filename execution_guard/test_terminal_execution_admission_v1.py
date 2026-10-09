import json
import tempfile
import unittest
from pathlib import Path

from execution_guard import terminal_execution_admission_v1 as guard


BASE_WORKFLOW = """\
persist-credentials: false
rm -rf llama.cpp
git init llama.cpp
git -C llama.cpp fetch --depth 1 origin abc
rm -rf llama.cpp/build
cmake -S llama.cpp -B llama.cpp/build
cmake --build llama.cpp/build
nohup llama.cpp/build/bin/llama-server
echo $! > LOCAL_QWEN_SERVER.pid
kill -0 "$(cat LOCAL_QWEN_SERVER.pid)"
http://127.0.0.1:8080/health
SYNTHETIC_COMPLETION.json
rank15_prestart_token_guard_v2.py
canonical.runtime.harbor_science_agent_v2:HarborScienceAgent
harbor run
"""


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "execution_guard").mkdir()
        (self.root / ".github/workflows").mkdir(parents=True)
        (self.root / "capsules/proof").mkdir(parents=True)
        (self.root / "capsules/rank15").mkdir(parents=True)
        self.old_root = guard.ROOT
        guard.ROOT = self.root

        self.workflow_rel = ".github/workflows/rank15.yml"
        self.workflow = self.root / self.workflow_rel
        self.workflow.write_text(BASE_WORKFLOW)

        repair = self.root / "capsules/proof/repair.json"
        verification = self.root / "capsules/proof/verification.json"
        authority = self.root / "capsules/rank15/authority.json"
        ledger = self.root / "capsules/rank15/ledger.json"
        admission_guard = self.root / "execution_guard/admission_guard.py"
        for p, body in [
            (repair, {"repair": True}),
            (verification, {"verification": True}),
            (authority, {"authority": True}),
            (ledger, {"ledger": True}),
            (admission_guard, {"guard": True}),
        ]:
            p.write_text(json.dumps(body) + "\n")

        self.invariant_rel = "execution_guard/CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1.json"
        invariant = {
            "schema": "PROJECT_BRAIN_CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1",
            "invariants": [{
                "id": "CPU",
                "scope": "TB_SCIENCE_LOCAL_QWEN_CPU_CARRIERS",
                "requires": {
                    "cache_compiled_build_directory": False,
                    "configure_on_current_runner": True,
                },
                "proof": {
                    "repair_path": "capsules/proof/repair.json",
                    "repair_git_blob_sha": guard.git_blob(repair),
                    "independent_verification_path": "capsules/proof/verification.json",
                    "independent_verification_git_blob_sha": guard.git_blob(verification),
                },
            }],
        }
        invariant_path = self.root / self.invariant_rel
        invariant_path.write_text(json.dumps(invariant, indent=2, sort_keys=True) + "\n")

        self.behavior_rel = "execution_guard/behavior.json"
        behavior = {
            "scope": "TB_SCIENCE_LOCAL_QWEN_CPU_CARRIERS",
            "slot_id": "S",
            "task_digest": "D",
            "workflow_path": self.workflow_rel,
            "behavior": {
                "cache_compiled_build_directory": False,
                "configure_on_current_runner": True,
            },
            "runtime_bindings": {
                "planner": {"path": "capsules/proof/repair.json", "git_blob_sha": guard.git_blob(repair)},
                "agent": {"path": "capsules/proof/verification.json", "git_blob_sha": guard.git_blob(verification)},
                "prestart_guard": {"path": "capsules/rank15/authority.json", "git_blob_sha": guard.git_blob(authority)},
                "transport": {"path": "capsules/rank15/ledger.json", "git_blob_sha": guard.git_blob(ledger)},
                "zero_exposure_tests": {"path": "capsules/proof/repair.json", "git_blob_sha": guard.git_blob(repair)},
            },
        }
        behavior_path = self.root / self.behavior_rel
        behavior_path.write_text(json.dumps(behavior, indent=2, sort_keys=True) + "\n")

        self.surface_rel = guard.SURFACE_PATH
        self.surface = {
            "schema": "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1",
            "active": True,
            "slot_id": "S",
            "task_digest": "D",
            "workflow_path": self.workflow_rel,
            "workflow_git_blob_sha": guard.git_blob(self.workflow),
            "activation_path": "capsules/rank15/ACTIVATE.json",
            "behavior": {"path": self.behavior_rel, "git_blob_sha": guard.git_blob(behavior_path)},
            "authority": {"path": "capsules/rank15/authority.json", "git_blob_sha": guard.git_blob(authority)},
            "ledger": {"path": "capsules/rank15/ledger.json", "git_blob_sha": guard.git_blob(ledger)},
            "invariant_registry": {"path": self.invariant_rel, "git_blob_sha": guard.git_blob(invariant_path)},
            "admission_guard": {"path": "execution_guard/admission_guard.py", "git_blob_sha": guard.git_blob(admission_guard)},
            "execution_authority": False,
        }
        self._write_surface()

    def tearDown(self):
        guard.ROOT = self.old_root
        self.tmp.cleanup()

    def _write_surface(self):
        (self.root / self.surface_rel).write_text(
            json.dumps(self.surface, indent=2, sort_keys=True) + "\n"
        )

    def test_staged_surface_passes_without_execution_authority_requirement(self):
        self.assertEqual(
            guard.admission_errors(
                workflow_rel=self.workflow_rel,
                slot_id="S",
                task_digest="D",
                require_activation=False,
                require_execution_authority=False,
            ),
            [],
        )

    def test_execution_fails_closed_while_surface_is_staged(self):
        errors = guard.admission_errors(
            workflow_rel=self.workflow_rel,
            slot_id="S",
            task_digest="D",
            require_activation=False,
            require_execution_authority=True,
        )
        self.assertIn("EXECUTION_AUTHORITY_NOT_ACTIVE", errors)

    def test_compiled_binary_cache_regression_is_rejected(self):
        text = BASE_WORKFLOW.replace(
            "rm -rf llama.cpp",
            "path: llama.cpp\\nbrain-llama-cpp\\nrm -rf llama.cpp",
            1,
        )
        self.workflow.write_text(text)
        self.surface["workflow_git_blob_sha"] = guard.git_blob(self.workflow)
        self._write_surface()
        errors = guard.admission_errors(
            workflow_rel=self.workflow_rel,
            slot_id="S",
            task_digest="D",
            require_activation=False,
            require_execution_authority=False,
        )
        self.assertTrue(any(x.startswith("WORKFLOW_FORBIDDEN:") for x in errors), errors)

    def test_semantic_invariant_violation_is_rejected_even_if_hashes_match(self):
        path = self.root / self.behavior_rel
        body = json.loads(path.read_text())
        body["behavior"]["cache_compiled_build_directory"] = True
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        self.surface["behavior"]["git_blob_sha"] = guard.git_blob(path)
        self._write_surface()
        errors = guard.admission_errors(
            workflow_rel=self.workflow_rel,
            slot_id="S",
            task_digest="D",
            require_activation=False,
            require_execution_authority=False,
        )
        self.assertTrue(any(x.startswith("INVARIANT_VIOLATION:CPU:cache_compiled_build_directory") for x in errors), errors)

    def test_workflow_blob_drift_is_rejected(self):
        self.workflow.write_text(BASE_WORKFLOW + "\n# drift\n")
        errors = guard.admission_errors(
            workflow_rel=self.workflow_rel,
            slot_id="S",
            task_digest="D",
            require_activation=False,
            require_execution_authority=False,
        )
        self.assertIn("SURFACE_WORKFLOW_BLOB_MISMATCH", errors)

    def test_phase_reordering_is_rejected(self):
        text = BASE_WORKFLOW.replace(
            "http://127.0.0.1:8080/health\nSYNTHETIC_COMPLETION.json\nrank15_prestart_token_guard_v2.py",
            "rank15_prestart_token_guard_v2.py\nhttp://127.0.0.1:8080/health\nSYNTHETIC_COMPLETION.json",
        )
        self.workflow.write_text(text)
        self.surface["workflow_git_blob_sha"] = guard.git_blob(self.workflow)
        self._write_surface()
        errors = guard.admission_errors(
            workflow_rel=self.workflow_rel,
            slot_id="S",
            task_digest="D",
            require_activation=False,
            require_execution_authority=False,
        )
        self.assertIn("WORKFLOW_PHASE_ORDER_INVALID", errors)

    def test_activation_requirement_is_fail_closed(self):
        errors = guard.admission_errors(
            workflow_rel=self.workflow_rel,
            slot_id="S",
            task_digest="D",
            require_activation=True,
            require_execution_authority=False,
        )
        self.assertIn("ACTIVATION_FILE_MISSING", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
