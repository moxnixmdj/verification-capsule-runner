from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/H100_ZERO_LEARNED_ROLE_INDUCTION_PREEXPOSURE_V1.json": "1d8049556eb073007e1f4686a3034726aeb27698",
    "canonical/runtime/h100_zero_learned_role_induction_v1.py": "f18cbb1a1d9e1f1184a06df536a09ba99f3fdfed",
    "canonical/tests/test_h100_zero_learned_role_induction_v1.py": "bfabb4171b207a36d2a2916e74e9d873b0acf9d1",
    "canonical/governance/H100_ZERO_LEARNED_ROLE_INDUCTION_CANDIDATE_V1.json": "e0c4d334af10f51ec3f28ba1eb356d3fd7297ae9",
}

def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()

def load_module():
    path = ROOT / "canonical/runtime/h100_zero_learned_role_induction_v1.py"
    spec = importlib.util.spec_from_file_location("h100_role", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main() -> None:
    for rel, expected in EXPECTED.items():
        actual = git_blob_sha((ROOT / rel).read_bytes())
        if actual != expected:
            raise SystemExit(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")

    pre = json.loads((ROOT / "canonical/governance/H100_ZERO_LEARNED_ROLE_INDUCTION_PREEXPOSURE_V1.json").read_text())
    cand = json.loads((ROOT / "canonical/governance/H100_ZERO_LEARNED_ROLE_INDUCTION_CANDIDATE_V1.json").read_text())
    if pre["status"] != "FROZEN_BEFORE_ROLE_INDUCTION_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT":
        raise SystemExit("PREEXPOSURE_STATUS_INVALID")
    if len(pre["tasks"]) != 6:
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")

    module = load_module()
    solved = 0
    abstained = 0
    for task in pre["tasks"]:
        out = module.induce_roles(task["payload"], format_hint=task["format"])
        if out["status"] != task["expected_status"]:
            raise SystemExit("STATUS_MISMATCH:" + task["task_id"])
        if out["inputs"] != task["expected_inputs"] or out["target"] != task["expected_target"]:
            raise SystemExit("ROLE_MISMATCH:" + task["task_id"])
        if out["persistent_learned_bytes"] != 0:
            raise SystemExit("LEARNED_BYTES_NONZERO:" + task["task_id"])
        if out["external_frontier_model_calls"] != 0 or out["external_learned_capability_calls"] != 0:
            raise SystemExit("EXTERNAL_LEARNED_PROVIDER_USED:" + task["task_id"])
        if out["status"] == "ABSTAIN_DIRECTION_NOT_IDENTIFIED":
            abstained += 1
        else:
            solved += 1

    if solved != 5 or abstained != 1:
        raise SystemExit("TASK_OUTCOME_COUNTS_INVALID")

    if cand["accounting"]["persistent_learned_bytes"] != 0:
        raise SystemExit("CANDIDATE_LEARNED_BYTES_NONZERO")
    if cand["preexposure"]["git_blob_sha"] != EXPECTED["canonical/governance/H100_ZERO_LEARNED_ROLE_INDUCTION_PREEXPOSURE_V1.json"]:
        raise SystemExit("CANDIDATE_PREEXPOSURE_BINDING_INVALID")

    print(json.dumps({
        "status": "PASS",
        "exact_subject_blobs": True,
        "identified_role_tasks": solved,
        "mandatory_abstentions": abstained,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "hard_nonclaim": "STRUCTURAL_ROLE_CUES_ARE_NOT_OPEN_WORLD_SEMANTIC_UNDERSTANDING",
    }, sort_keys=True))

if __name__ == "__main__":
    main()
