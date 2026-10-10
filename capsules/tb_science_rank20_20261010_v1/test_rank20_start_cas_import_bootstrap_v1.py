from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py"


def test_start_cas_wrapper_bootstraps_repository_imports_without_cwd_help():
    old_cwd = Path.cwd()
    old_path = list(sys.path)
    removed = {}
    prefixes = (
        "execution_guard",
        "terminal_slot_start_cas_v1",
        "terminal_slot_start_cas_v2",
        "github_status_object_store_v1",
        "rank20_claim_bound_identity_v1",
    )
    try:
        sys.path[:] = [
            row for row in old_path
            if row and Path(row).resolve() not in {ROOT.resolve(), (ROOT / "execution_guard").resolve()}
        ]
        for name in list(sys.modules):
            if name == prefixes[0] or any(name == p or name.startswith(p + ".") for p in prefixes):
                removed[name] = sys.modules.pop(name)
        os.chdir("/")
        runpy.run_path(str(WRAPPER), run_name="rank20_start_cas_import_probe")
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path
        for name, module in removed.items():
            sys.modules[name] = module

    assert not (ROOT / "RANK20_START_CAS_CHECK_V7.json").exists()
    assert not (ROOT / "RANK20_START_CAS_V7.json").exists()
