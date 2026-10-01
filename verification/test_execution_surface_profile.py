import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "session_bridge"))
import controller_fast


class ExecutionSurfaceProfileTests(unittest.TestCase):
    def test_pep668_profile_is_reported_from_exact_container(self):
        raw = {
            "python_present": True,
            "python_executable": "/usr/bin/python3",
            "python_version": "3.12.3",
            "python_implementation": "CPython",
            "stdlib_path": "/usr/lib/python3.12",
            "externally_managed_marker_present": True,
            "externally_managed_marker_path": "/usr/lib/python3.12/EXTERNALLY-MANAGED",
            "pip_module_present": True,
            "venv_module_present": True,
            "os_id": "ubuntu",
            "os_version_id": "24.04",
        }
        cp = SimpleNamespace(returncode=0, stdout=json.dumps(raw), stderr="")
        with patch.object(controller_fast.legacy, "run", return_value=cp) as run:
            got = controller_fast.collect_execution_surface_profile()
        self.assertEqual(got["status"], "OK")
        self.assertEqual(got["system_pip_mutation_policy"], "PEP668_EXTERNALLY_MANAGED")
        self.assertEqual(len(got["profile_sha256"]), 64)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:4], ["docker", "exec", "brain-bridge-task", "python3"])

    def test_non_pep668_surface_is_distinguished(self):
        raw = {
            "python_present": True,
            "python_executable": "/opt/python/bin/python3",
            "python_version": "3.12.7",
            "python_implementation": "CPython",
            "stdlib_path": "/opt/python/lib/python3.12",
            "externally_managed_marker_present": False,
            "externally_managed_marker_path": "/opt/python/lib/python3.12/EXTERNALLY-MANAGED",
            "pip_module_present": True,
            "venv_module_present": True,
            "os_id": "ubuntu",
            "os_version_id": "24.04",
        }
        cp = SimpleNamespace(returncode=0, stdout=json.dumps(raw), stderr="")
        with patch.object(controller_fast.legacy, "run", return_value=cp):
            got = controller_fast.collect_execution_surface_profile()
        self.assertEqual(got["system_pip_mutation_policy"], "NO_PEP668_EXTERNALLY_MANAGED_MARKER")

    def test_probe_failure_is_fail_visible(self):
        cp = SimpleNamespace(returncode=127, stdout="", stderr="python3: not found")
        with patch.object(controller_fast.legacy, "run", return_value=cp):
            got = controller_fast.collect_execution_surface_profile()
        self.assertEqual(got["status"], "PYTHON_PROFILE_UNAVAILABLE")
        self.assertFalse(got["python_present"])
        self.assertEqual(got["probe_exit_code"], 127)


if __name__ == "__main__":
    unittest.main(verbosity=2)
