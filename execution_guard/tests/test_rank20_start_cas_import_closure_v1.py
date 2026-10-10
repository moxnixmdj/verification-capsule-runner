from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"


class Rank20StartCASImportClosureTests(unittest.TestCase):
    def test_direct_script_imports_with_pythonpath_unset(self):
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("ModuleNotFoundError", proc.stderr)
        self.assertIn("--check-absent", proc.stdout)
        self.assertIn("--acquire", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
