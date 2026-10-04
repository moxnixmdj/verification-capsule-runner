#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subjects" / "local_semantic_core_v1"

EXPECTED = {
    "canonical/runtime/local_semantic_text_core_v1.py":
        "06fb776606743748cbb257ff2bf80cc5d441c9ed",
    "canonical/tests/test_local_semantic_text_core_v1.py":
        "c5af80e7ba77fe48c0c253f41378669850d69084",
    "canonical/runtime/root2_livebench_if_astra_inference_adapter_v4.py":
        "6006c64b396cc8907ab854d44dd58fbb2e5aff7c",
    "canonical/tests/test_root2_livebench_if_astra_inference_adapter_v4.py":
        "f64f36e10a684a8644084cf464a0c58425468d37",
    "canonical/runtime/seed_preserving_instruction_postprocessor_v2.py":
        "b766cefd5e7f23d2533ff49d1c259eb83a0a53f0",
    "canonical/runtime/seed_preserving_instruction_postprocessor_v1.py":
        "8cdb308941dbd6711279cbd1d505aca6aabdd376",
    "canonical/runtime/instruction_constraint_compiler_v1.py":
        "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}

def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

for rel, want in EXPECTED.items():
    path = SUBJECT / rel
    if not path.is_file():
        raise SystemExit("FAIL_CLOSED:MISSING_SUBJECT:" + rel)
    got = git_blob(path)
    if got != want:
        raise SystemExit(f"FAIL_CLOSED:BLOB_MISMATCH:{rel}:{got}:{want}")
    ast.parse(path.read_text(encoding="utf-8"), filename=rel)

core_src = (SUBJECT / "canonical/runtime/local_semantic_text_core_v1.py").read_text()
core_tree = ast.parse(core_src)
for node in ast.walk(core_tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        names = []
        if isinstance(node, ast.Import):
            names = [x.name.split(".")[0] for x in node.names]
        else:
            names = [(node.module or "").split(".")[0]]
        forbidden = {"socket","requests","urllib","httpx","subprocess","torch","transformers"}
        if forbidden.intersection(names):
            raise SystemExit("FAIL_CLOSED:SEMANTIC_CORE_FORBIDDEN_IMPORT")

v4_path = SUBJECT / "canonical/runtime/root2_livebench_if_astra_inference_adapter_v4.py"
v4_tree = ast.parse(v4_path.read_text())
for node in ast.walk(v4_tree):
    # The evaluated-model ABI must not consume grader-only metadata.
    if isinstance(node, ast.Constant) and node.value in {"instruction_id_list", "kwargs"}:
        raise SystemExit("FAIL_CLOSED:V4_GRADER_ONLY_METADATA_REFERENCE")

env = os.environ.copy()
env["PYTHONPATH"] = str(SUBJECT)
cmd = [
    sys.executable, "-m", "unittest", "-v",
    "canonical.tests.test_local_semantic_text_core_v1",
    "canonical.tests.test_root2_livebench_if_astra_inference_adapter_v4",
]
cp = subprocess.run(cmd, cwd=SUBJECT, env=env, text=True)
if cp.returncode != 0:
    raise SystemExit(cp.returncode)

print("PASS:LOCAL_SEMANTIC_CORE_V1_EXACT_SUBJECT_AND_V4_COMPOSITION")
