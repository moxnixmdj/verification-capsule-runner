#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "sub100mb_learned_state_v1"

EXPECTED_GIT_BLOBS = {
    "CONTRACT.json": "fc994d2cd4fb964a97df7706dd19d6519131cf72",
    "auditor.py": "bfd57d90fbf30f68301103a0fa5549c9e589227b",
    "source_tests.py": "176eb10d9d8f7e6c930f8daa82c6aec9c68977cb",
    "DKL_AUDIT.json": "89631516466f698ea7afaa166b36ff2311441e49",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


for name, expected in EXPECTED_GIT_BLOBS.items():
    data = (SUBJECT / name).read_bytes()
    actual = git_blob_sha(data)
    assert actual == expected, (name, actual, expected)

contract = json.loads((SUBJECT / "CONTRACT.json").read_text())
assert contract["schema"] == "PROJECT_BRAIN_SUB100MB_LEARNED_STATE_CONTRACT_V1"
assert contract["hard_budget"]["max_bytes_exclusive"] == 100_000_000
assert contract["acceptance_binding"]["target_families"] == 19
assert contract["acceptance_binding"]["target_atomic_predicates"] == 38
assert contract["authority"] == {
    "execution": False,
    "promotion": False,
    "acceptance_credit": False,
    "family_credit": False,
    "capability_credit": False,
    "ownership_credit": False,
}

audit_doc = json.loads((SUBJECT / "DKL_AUDIT.json").read_text())
assert audit_doc["schema"] == "PROJECT_BRAIN_SUB100MB_DKL_DEPENDENCY_AUDIT_V1"
assert audit_doc["first_falsification_wedge"]["builder_must_not_use_hidden_verifier_metrics"] is True
assert "UNKNOWN_MECHANISM_DEFAULTS_TO_L_NOT_D" in audit_doc["hard_rules"]
assert "DATA_FIT_OR_OPTIMIZED_STATE_ALWAYS_COUNTS_AS_L" in audit_doc["hard_rules"]

spec = importlib.util.spec_from_file_location("sub100mb_auditor", SUBJECT / "auditor.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

def base_manifest():
    return {
        "schema": mod.MANIFEST_SCHEMA,
        "capsule_id": "independent-runner-capsule",
        "inventory_complete": True,
        "dependency_closure_complete": True,
        "same_capsule_for_all_predicates": True,
        "frozen_acceptance_predicate_count": 38,
        "artifacts": [],
        "runtime_providers": [],
    }

# Strict byte boundary.
m = base_manifest()
m["artifacts"] = [{
    "path": "kernel.bin",
    "sha256": "0" * 64,
    "bytes": 99_999_999,
    "classification": "LEARNED",
    "learned_kind": "MODEL_WEIGHTS",
}]
x = mod.audit_manifest(m)
assert x["under_budget"] is True and x["learned_bytes"] == 99_999_999
assert x["manifest_mechanically_complete"] is True

m["artifacts"][0]["bytes"] = 100_000_000
x = mod.audit_manifest(m)
assert x["under_budget"] is False
assert "LEARNED_STATE_BUDGET_EXCEEDED" in x["reasons"]

# Learned state cannot be relabeled static.
m = base_manifest()
m["artifacts"] = [{
    "path": "router.dat",
    "sha256": "0" * 64,
    "bytes": 1,
    "classification": "NONLEARNED",
    "deterministic_or_static": True,
    "fit_or_optimized_from_data": True,
}]
x = mod.audit_manifest(m)
assert any("MISCLASSIFIED_AS_NONLEARNED" in r for r in x["reasons"])

# External general reasoning/capability substitution is forbidden.
m = base_manifest()
m["runtime_providers"] = [{
    "role": "REMOTE_FRONTIER_MODEL",
    "external": True,
    "learned_general_reasoning": True,
    "supplies_missing_target_capability": True,
}]
x = mod.audit_manifest(m)
assert any("FORBIDDEN_PROVIDER_ROLE" in r for r in x["reasons"])
assert any("SUPPLIES_MISSING_TARGET_CAPABILITY" in r for r in x["reasons"])

# Path traversal and duplicate inventory fail closed.
m = base_manifest()
m["artifacts"] = [
    {
        "path": "../escape.bin",
        "sha256": "0" * 64,
        "bytes": 1,
        "classification": "LEARNED",
        "learned_kind": "MODEL_WEIGHTS",
    },
    {
        "path": "dup.bin",
        "sha256": "0" * 64,
        "bytes": 1,
        "classification": "LEARNED",
        "learned_kind": "MODEL_WEIGHTS",
    },
    {
        "path": "dup.bin",
        "sha256": "0" * 64,
        "bytes": 1,
        "classification": "LEARNED",
        "learned_kind": "MODEL_WEIGHTS",
    },
]
x = mod.audit_manifest(m)
assert any("INVALID_PATH" in r for r in x["reasons"])
assert "DUPLICATE_ARTIFACT_PATH:dup.bin" in x["reasons"]

# Exact state-root accounting and undeclared-file detection.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    learned = b"independent tiny kernel"
    static = b'{"rule":"deterministic"}'
    (root / "kernel.bin").write_bytes(learned)
    (root / "rules.json").write_bytes(static)

    m = base_manifest()
    m["artifacts"] = [
        {
            "path": "kernel.bin",
            "sha256": sha256(learned),
            "bytes": len(learned),
            "classification": "LEARNED",
            "learned_kind": "MODEL_WEIGHTS",
        },
        {
            "path": "rules.json",
            "sha256": sha256(static),
            "bytes": len(static),
            "classification": "NONLEARNED",
            "deterministic_or_static": True,
            "fit_or_optimized_from_data": False,
        },
    ]
    x = mod.audit_state_root(root, m)
    assert x["exact_state_root_verified"] is True
    assert x["learned_bytes"] == len(learned)

    (root / "hidden.bin").write_bytes(b"hidden")
    x = mod.audit_state_root(root, m)
    assert x["exact_state_root_verified"] is False
    assert "UNDECLARED_STATE_FILE:hidden.bin" in x["reasons"]

# Capacity helper is planning-only but arithmetic must be exact.
assert mod.theoretical_parameter_capacity(16) == 50_000_000
assert mod.theoretical_parameter_capacity(8) == 100_000_000
assert mod.theoretical_parameter_capacity(4) == 200_000_000

print(json.dumps({
    "status": "PASS",
    "exact_subject_blobs": len(EXPECTED_GIT_BLOBS),
    "strict_budget_bytes_exclusive": mod.MAX_LEARNED_BYTES_EXCLUSIVE,
    "frozen_acceptance_predicates": 38,
    "adversarial_classes_checked": [
        "strict_boundary",
        "misclassified_learned_state",
        "external_reasoning_substitution",
        "path_traversal",
        "duplicate_inventory",
        "undeclared_state_file",
        "exact_hash_and_size",
    ],
    "acceptance_credit_delta": 0,
    "capability_credit_delta": 0,
}, indent=2))
