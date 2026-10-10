from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAS = ROOT / "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"
PREFLIGHT = ROOT / "capsules/tb_science_rank20_20261010_v1/rank20_execution_preflight_v7.py"
RETIRED_BRANCH = "execute/tb-science-rank20-20261010-v2"
RETIRED_ACTIVATION = "ACTIVATE_RANK20_V2_PR.json"


class Rank20GenerationNeutralGateTests(unittest.TestCase):
    def test_gate_source_contains_no_retired_activation_identity(self):
        cas = CAS.read_text(encoding="utf-8")
        preflight = PREFLIGHT.read_text(encoding="utf-8")
        for text in (cas, preflight):
            self.assertNotIn(RETIRED_BRANCH, text)
            self.assertNotIn(RETIRED_ACTIVATION, text)
            ast.parse(text)

    def test_start_cas_uses_authority_derived_epoch_and_activation_checks(self):
        text = CAS.read_text(encoding="utf-8")
        self.assertIn(
            'epoch.get("execution_branch") != expected_head',
            text,
        )
        self.assertIn(
            'claim.get("execution_branch") != expected_head',
            text,
        )
        self.assertIn(
            'claim.get("activation_filename") != expected_activation_filename',
            text,
        )

    def test_direct_start_cas_import_remains_pythonpath_independent(self):
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        proc = subprocess.run(
            [sys.executable, str(CAS), "--help"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("ModuleNotFoundError", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
