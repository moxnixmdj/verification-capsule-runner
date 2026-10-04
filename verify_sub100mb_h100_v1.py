from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "sub100mb_h100_v1_20261004_sol"
RUNTIME = SUBJECT / "sub100mb_learned_state_guard_v1.py"
TESTS = SUBJECT / "test_sub100mb_learned_state_guard_v1.py"
CONTRACT = SUBJECT / "SUB100MB_LEARNED_CORE_EXPERIMENT_CONTRACT_V1.json"

EXPECTED_RUNTIME_GIT_BLOB = "0e6279ddbaf6c23856d37869fa9e39c1b25fa82c"
EXPECTED_TESTS_GIT_BLOB = "e1d621c1528b3c33828eefd506ecf9aa185666ae"
EXPECTED_CONTRACT_GIT_BLOB = "34a7d9f2629712ffdc4082ceea92324ed6e76112"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(payload).hexdigest()


assert git_blob_sha(RUNTIME) == EXPECTED_RUNTIME_GIT_BLOB
assert git_blob_sha(TESTS) == EXPECTED_TESTS_GIT_BLOB
assert git_blob_sha(CONTRACT) == EXPECTED_CONTRACT_GIT_BLOB

contract = json.loads(CONTRACT.read_text())
assert contract["schema"] == "PROJECT_BRAIN_SUB100MB_LEARNED_CORE_EXPERIMENT_CONTRACT_V1"
assert contract["hypothesis_id"] == "H100_FRONTIER_CAPABILITY_WITH_LE_100000000_PERSISTENT_LEARNED_BYTES"
assert contract["frozen_resource_definition"]["max_persistent_learned_bytes"] == 100_000_000
assert contract["terminal_success"]["accepted_families_required"] == 19
assert contract["terminal_success"]["verified_owned_families_required"] == 19
assert contract["terminal_success"]["proved_atomic_required"] == 38
assert contract["baseline"]["ownership_matrix"]["accepted_families"] == 5
assert contract["baseline"]["ownership_matrix"]["verified_owned_families"] == 5
assert contract["baseline"]["terminal_root_state"]["proved_atomic"] == 12
assert contract["provider_boundary"]["external_frontier_model_calls_during_scored_execution"] == 0
assert contract["provider_boundary"]["external_learned_capability_calls_during_scored_execution"] == 0
assert contract["execution_authority"] is False
assert contract["promotion_authority"] is False
assert contract["fresh_reality_authority"] is False

spec = importlib.util.spec_from_file_location("h100_guard", RUNTIME)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

assert mod.MAX_LEARNED_BYTES == 100_000_000
assert mod.FROZEN_FAMILY_COUNT == 19
assert mod.FROZEN_ATOMIC_COUNT == 38
assert mod.HYPOTHESIS_ID == contract["hypothesis_id"]


def base() -> dict:
    return {
        "schema": mod.INPUT_SCHEMA,
        "hypothesis_id": mod.HYPOTHESIS_ID,
        "max_persistent_learned_bytes": mod.MAX_LEARNED_BYTES,
        "learned_artifacts": [
            {
                "id": "kernel",
                "path": "artifacts/kernel.bin",
                "bytes": 80_000_000,
                "sha256": "a" * 64,
            }
        ],
        "runtime_dependencies": [
            {"id": "kernel-runtime", "kind": "learned_component", "artifact_id": "kernel"},
            {"id": "python", "kind": "executor"},
            {"id": "docs", "kind": "raw_knowledge_source"},
        ],
        "scored_execution": {
            "external_frontier_model_calls": 0,
            "external_learned_capability_calls": 0,
        },
        "capability_contract": {
            "accepted_families": 19,
            "verified_owned_families": 19,
            "total_families": 19,
            "proved_atomic": 38,
            "total_atomic": 38,
        },
    }


# Positive close at <=100 MB and complete 19/38 contract.
out = mod.audit(base())
assert out["pass"] is True, out
assert out["status"] == "H100_CLOSED"
assert out["learned_bytes_total"] == 80_000_000

# Exact boundary is allowed.
d = base()
d["learned_artifacts"][0]["bytes"] = 100_000_000
out = mod.audit(d)
assert out["pass"] is True
assert out["learned_bytes_headroom"] == 0

# One byte over must fail.
d = base()
d["learned_artifacts"][0]["bytes"] = 100_000_001
out = mod.audit(d)
assert out["pass"] is False
assert out["status"] == "CANDIDATE_REJECTED"
assert out["budget_pass"] is False

# Hiding learned capability behind a remote frontier provider must fail.
d = base()
d["runtime_dependencies"].append({"id": "remote-frontier", "kind": "external_frontier_model"})
out = mod.audit(d)
assert out["pass"] is False
assert out["provider_boundary_pass"] is False
assert out["forbidden_runtime_dependencies"] == ["remote-frontier"]

# Calling an external learned capability provider must fail even if not listed as a dependency.
d = base()
d["scored_execution"]["external_learned_capability_calls"] = 1
out = mod.audit(d)
assert out["pass"] is False
assert out["provider_boundary_pass"] is False

# Any local learned component must map to a counted artifact.
d = base()
d["runtime_dependencies"][0]["artifact_id"] = "hidden-kernel"
out = mod.audit(d)
assert out["status"] == "FAIL_CLOSED"
assert "LEARNED_COMPONENT_NOT_COUNTED:kernel-runtime" in out["errors"]

# Denominator shrinkage must fail closed.
d = base()
d["capability_contract"]["total_families"] = 5
out = mod.audit(d)
assert out["status"] == "FAIL_CLOSED"
assert "FAMILY_DENOMINATOR_CHANGED" in out["errors"]

d = base()
d["capability_contract"]["total_atomic"] = 12
out = mod.audit(d)
assert out["status"] == "FAIL_CLOSED"
assert "ATOMIC_DENOMINATOR_CHANGED" in out["errors"]

# Current Brain baseline must remain open, not be promoted by the budget guard.
d = base()
d["capability_contract"].update(
    accepted_families=5,
    verified_owned_families=5,
    proved_atomic=12,
)
out = mod.audit(d)
assert out["pass"] is False
assert out["status"] == "EXPERIMENT_OPEN"
assert out["budget_pass"] is True
assert out["provider_boundary_pass"] is True
assert out["capability_pass"] is False

# Raw knowledge remains allowed as knowledge, while the contract explicitly forbids
# task-specific reasoning/capability substitution through that channel.
assert any(x["kind"] == "raw_knowledge_source" for x in base()["runtime_dependencies"])
assert "MUST_NOT_SUPPLY_TASK_SPECIFIC_REASONING" in contract["provider_boundary"]["raw_knowledge_rule"]

print("PASS: exact H100 candidate blobs verified")
print("PASS: 100,000,000-byte learned-state boundary is exact and fail-closed")
print("PASS: external learned/frontier capability providers are rejected")
print("PASS: hidden uncounted learned components are rejected")
print("PASS: 19-family / 38-atom denominators cannot be shrunk")
print("PASS: current 5/19, 12/38 baseline remains experiment-open with zero credit")
