from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/H100_ZERO_LEARNED_SCHEMA_STRESS_PREEXPOSURE_V1.json": "4c0e2b160f04a75baf9825534530ade440f6b127",
    "canonical/runtime/h100_zero_learned_schema_compiler_v1.py": "7a0bf9b4a249ec807ba34a7c3c323b1603d39dd9",
    "canonical/tests/test_h100_zero_learned_schema_compiler_v1.py": "c4ce8ec8155b46accbc79a284ae192b3d37198b5",
    "canonical/governance/H100_ZERO_LEARNED_SCHEMA_COMPILER_CANDIDATE_V1.json": "460d4f76d149fa95f42430ea115862fd42a481a9",
}


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def load_module():
    path = ROOT / "canonical/runtime/h100_zero_learned_schema_compiler_v1.py"
    spec = importlib.util.spec_from_file_location("h100_schema", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    for rel, expected in EXPECTED.items():
        data = (ROOT / rel).read_bytes()
        actual = git_blob_sha(data)
        if actual != expected:
            raise SystemExit(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")

    pre = json.loads((ROOT / "canonical/governance/H100_ZERO_LEARNED_SCHEMA_STRESS_PREEXPOSURE_V1.json").read_text())
    cand = json.loads((ROOT / "canonical/governance/H100_ZERO_LEARNED_SCHEMA_COMPILER_CANDIDATE_V1.json").read_text())
    if pre["status"] != "FROZEN_BEFORE_COMPILER_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT":
        raise SystemExit("PREEXPOSURE_STATUS_INVALID")
    if pre["task_count"] != 8 or len(pre["tasks"]) != 8:
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")

    module = load_module()
    solved = 0
    for task in pre["tasks"]:
        out = module.compile_observations(
            task["payload"],
            inputs=task["expected_inputs"],
            target=task["target"],
            format_hint=task["format"],
        )
        if out["status"] != "TYPED_NUMERIC_SCHEMA_COMPILED":
            raise SystemExit("TASK_NOT_COMPILED:" + task["task_id"])
        if out["inputs"] != task["expected_inputs"] or out["target"] != task["target"]:
            raise SystemExit("SCHEMA_MISMATCH:" + task["task_id"])
        if out["persistent_learned_bytes"] != 0:
            raise SystemExit("LEARNED_BYTES_NONZERO:" + task["task_id"])
        if out["external_frontier_model_calls"] != 0 or out["external_learned_capability_calls"] != 0:
            raise SystemExit("EXTERNAL_LEARNED_PROVIDER_USED:" + task["task_id"])
        solved += 1

    accounting = cand["accounting"]
    if accounting["persistent_learned_bytes"] != 0:
        raise SystemExit("CANDIDATE_LEARNED_BYTES_NONZERO")
    if cand["preexposure"]["git_blob_sha"] != EXPECTED["canonical/governance/H100_ZERO_LEARNED_SCHEMA_STRESS_PREEXPOSURE_V1.json"]:
        raise SystemExit("CANDIDATE_PREEXPOSURE_BINDING_INVALID")
    if cand["exact_bound_components"]["canonical/runtime/h100_zero_learned_schema_compiler_v1.py"] != EXPECTED["canonical/runtime/h100_zero_learned_schema_compiler_v1.py"]:
        raise SystemExit("CANDIDATE_RUNTIME_BINDING_INVALID")
    if cand["exact_bound_components"]["canonical/tests/test_h100_zero_learned_schema_compiler_v1.py"] != EXPECTED["canonical/tests/test_h100_zero_learned_schema_compiler_v1.py"]:
        raise SystemExit("CANDIDATE_TEST_BINDING_INVALID")

    print(json.dumps({
        "status": "PASS",
        "exact_subject_blobs": True,
        "preexposed_tasks_solved": solved,
        "preexposed_task_count": 8,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "hard_nonclaim": "BOUNDED_SCHEMA_COMPILATION_IS_NOT_OPEN_WORLD_LANGUAGE_OR_SEMANTIC_ROLE_INDUCTION",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
