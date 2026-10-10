from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest

from execution_guard import bound_runtime_dispatch_v1 as dispatch
from capsules.tb_science_rank20_20261010_v1 import rank20_v8_status_journal_runner as runner


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_START_CAS_REL = "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v8.py"
EXPECTED_START_CAS_BLOB = "99d81c7d1316d1767c688e12c2c05790c69662f3"


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class BoundRuntimeDispatchTests(unittest.TestCase):
    def test_exact_promoted_surface_resolves_bound_v8_start_cas(self):
        out = dispatch.resolve_bound_runtime(root=ROOT, runtime_key="start_cas")
        self.assertEqual(out["runtime_rel"], EXPECTED_START_CAS_REL)
        self.assertEqual(out["runtime_git_blob_sha"], EXPECTED_START_CAS_BLOB)
        self.assertEqual(
            out["behavior_rel"] if "behavior_rel" in out else out["behavior_path"],
            "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V7.json",
        )

    def test_v8_runner_contains_no_hardcoded_v7_start_cas_path(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn('rank20_start_cas_v7.py', source)
        self.assertIn('resolve_bound_runtime(root=ROOT, runtime_key="start_cas")', source)

    def test_v8_runner_executes_resolved_runtime(self):
        called = {}
        old_resolve = runner.resolve_bound_runtime
        old_run = runner.subprocess.run
        try:
            runner.resolve_bound_runtime = lambda **_: {
                "runtime_path": str(ROOT / EXPECTED_START_CAS_REL)
            }
            def fake_run(argv, **kwargs):
                called["argv"] = argv
                called["kwargs"] = kwargs
                return types.SimpleNamespace(returncode=0)
            runner.subprocess.run = fake_run
            runner._acquire_start_commit()
        finally:
            runner.resolve_bound_runtime = old_resolve
            runner.subprocess.run = old_run
        self.assertEqual(called["argv"][1], str(ROOT / EXPECTED_START_CAS_REL))
        self.assertEqual(called["argv"][2], "--acquire")
        self.assertEqual(called["kwargs"]["cwd"], ROOT)

    def _fixture(self, root: Path) -> None:
        cas = root / "capsules/rank20_start_cas_v8.py"
        cas.parent.mkdir(parents=True, exist_ok=True)
        cas.write_text("print('cas')\n", encoding="utf-8")
        behavior = root / "execution_guard/behavior.json"
        write_json(behavior, {
            "runtime_bindings": {
                "start_cas": {
                    "path": "capsules/rank20_start_cas_v8.py",
                    "git_blob_sha": blob(cas),
                }
            }
        })
        surface = root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
        write_json(surface, {
            "behavior": {
                "path": "execution_guard/behavior.json",
                "git_blob_sha": blob(behavior),
            }
        })

    def test_stale_runtime_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            (root / "capsules/rank20_start_cas_v8.py").write_text("print('changed')\n", encoding="utf-8")
            with self.assertRaisesRegex(dispatch.BoundRuntimeDispatchError, "BOUND_BLOB_MISMATCH:runtime.start_cas"):
                dispatch.resolve_bound_runtime(root=root, runtime_key="start_cas")

    def test_stale_behavior_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            behavior = root / "execution_guard/behavior.json"
            doc = json.loads(behavior.read_text())
            doc["extra"] = True
            write_json(behavior, doc)
            with self.assertRaisesRegex(dispatch.BoundRuntimeDispatchError, "BOUND_BLOB_MISMATCH:surface.behavior"):
                dispatch.resolve_bound_runtime(root=root, runtime_key="start_cas")

    def test_missing_runtime_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            with self.assertRaisesRegex(dispatch.BoundRuntimeDispatchError, "BINDING_MISSING:runtime.missing"):
                dispatch.resolve_bound_runtime(root=root, runtime_key="missing")

    def test_path_escape_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            behavior = root / "execution_guard/behavior.json"
            b = json.loads(behavior.read_text())
            b["runtime_bindings"]["start_cas"] = {
                "path": "../outside.py",
                "git_blob_sha": "0" * 40,
            }
            write_json(behavior, b)
            surface = root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
            s = json.loads(surface.read_text())
            s["behavior"]["git_blob_sha"] = blob(behavior)
            write_json(surface, s)
            with self.assertRaisesRegex(dispatch.BoundRuntimeDispatchError, "BOUND_PATH_ESCAPE:runtime.start_cas"):
                dispatch.resolve_bound_runtime(root=root, runtime_key="start_cas")

    def test_symlink_runtime_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            target = root / "capsules/real.py"
            target.write_text("print('real')\n", encoding="utf-8")
            link = root / "capsules/link.py"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            behavior = root / "execution_guard/behavior.json"
            b = json.loads(behavior.read_text())
            b["runtime_bindings"]["start_cas"] = {
                "path": "capsules/link.py",
                "git_blob_sha": blob(target),
            }
            write_json(behavior, b)
            surface = root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
            s = json.loads(surface.read_text())
            s["behavior"]["git_blob_sha"] = blob(behavior)
            write_json(surface, s)
            with self.assertRaisesRegex(dispatch.BoundRuntimeDispatchError, "BOUND_SYMLINK_FORBIDDEN:runtime.start_cas"):
                dispatch.resolve_bound_runtime(root=root, runtime_key="start_cas")


if __name__ == "__main__":
    unittest.main(verbosity=2)
