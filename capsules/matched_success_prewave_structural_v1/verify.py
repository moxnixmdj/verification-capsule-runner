from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
AUTH = ROOT / "authority"

FILES = {
    SRC / "matched_case_isolation_reset_v1.py": "46df424bdaca0cf5276057ed7f286dccb8f589c4",
    SRC / "MATCHED_CASE_ISOLATION_RESET_CONTRACT_V1.json": "1ceef520c4022c6059abbb70923e8049801da192",
    SRC / "matched_success_scope_compiler_v1.py": "e10ad027ae6c44f587050362511cfaae31ff7f5c",
    SRC / "MATCHED_SUCCESS_SCOPE_COMPILER_V1.json": "2e344ccaa611cda7764d4d70557f1e5bdec9cf3c",
    AUTH / "OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json": "72a5cd689f55df84de73693371264f02ef4e7226",
}


def git_blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


for path, expected in FILES.items():
    actual = git_blob(path)
    assert actual == expected, (path, actual, expected)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


iso = load_module("iso_v1", SRC / "matched_case_isolation_reset_v1.py")
scope = load_module("scope_v1", SRC / "matched_success_scope_compiler_v1.py")
iso_gov = json.loads((SRC / "MATCHED_CASE_ISOLATION_RESET_CONTRACT_V1.json").read_text())
scope_gov = json.loads((SRC / "MATCHED_SUCCESS_SCOPE_COMPILER_V1.json").read_text())
norm = json.loads((AUTH / "OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json").read_text())

TARGETS = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

# Derive exact dimension basis independently from the frozen target normalization.
derived = {}
for row in norm["targets"]:
    pid = row["predicate_id"]
    if pid not in TARGETS:
        continue
    atoms = {
        source["atom"]
        for source in row["atom_sources"]
        if source["atom"].startswith("dimension:")
    }
    derived[pid] = atoms

assert set(derived) == TARGETS
assert derived == scope.REQUIRED
assert sum(len(v) for v in derived.values()) == 16
assert scope_gov["required_normalized_dimension_atom_count"] == 16
assert scope_gov["targets"] == {pid: len(derived[pid]) for pid in TARGETS}
assert scope_gov["authority"]["matched_target_normalization"]["git_blob_sha"] == FILES[
    AUTH / "OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json"
]

# Isolation happy path.
A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64

iso_base = {
    "schema": iso.INPUT_SCHEMA,
    "base": {
        "immutable_base_state_sha256": A,
        "brain_runtime_frozen": True,
        "opus_interface_frozen": True,
        "tool_authority_frozen": True,
        "read_only_shared_dependencies_only": True,
        "cross_case_persistent_memory_disabled": True,
        "cross_case_mutable_cache_disabled": True,
        "outbound_effects_case_namespaced": True,
        "case_namespace_destroyed_after_case": True,
        "external_mutable_services_resettable": True,
    },
    "cases": [
        {
            "case_id": "A",
            "immutable_base_state_sha256": A,
            "mutable_namespace_sha256": B,
            "case_initial_state_sha256": C,
            "brain_initial_state_sha256": C,
            "opus_initial_state_sha256": C,
            "prior_case_ids_consumed": [],
            "namespace_created_from_clean_base": True,
            "brain_run_confined_to_namespace": True,
            "future_opus_run_confined_to_same_namespace_semantics": True,
            "all_mutable_sinks_namespaced_or_restored": True,
            "post_case_namespace_destroyed": True,
            "external_mutable_state_restored": True,
            "no_result_dependent_case_generation": True,
            "no_result_dependent_runtime_mutation": True,
            "post_reset_base_state_sha256": A,
            "receipt": {"receipt_sha256": D, "independent_or_objective": True},
        },
        {
            "case_id": "B",
            "immutable_base_state_sha256": A,
            "mutable_namespace_sha256": E,
            "case_initial_state_sha256": F,
            "brain_initial_state_sha256": F,
            "opus_initial_state_sha256": F,
            "prior_case_ids_consumed": [],
            "namespace_created_from_clean_base": True,
            "brain_run_confined_to_namespace": True,
            "future_opus_run_confined_to_same_namespace_semantics": True,
            "all_mutable_sinks_namespaced_or_restored": True,
            "post_case_namespace_destroyed": True,
            "external_mutable_state_restored": True,
            "no_result_dependent_case_generation": True,
            "no_result_dependent_runtime_mutation": True,
            "post_reset_base_state_sha256": A,
            "receipt": {"receipt_sha256": B, "independent_or_objective": True},
        },
    ],
}

out = iso.compile_isolation(iso_base)
assert out["status"] == "PASS__CASE_ISOLATED_OR_RESET_EQUIVALENT"
assert out["residual_only_comparator_counterfactual_preserved"] is True

# Every boolean isolation gate must fail closed when falsified.
base_bool_keys = [
    "brain_runtime_frozen",
    "opus_interface_frozen",
    "tool_authority_frozen",
    "read_only_shared_dependencies_only",
    "cross_case_persistent_memory_disabled",
    "cross_case_mutable_cache_disabled",
    "outbound_effects_case_namespaced",
    "case_namespace_destroyed_after_case",
    "external_mutable_services_resettable",
]
case_bool_keys = [
    "namespace_created_from_clean_base",
    "brain_run_confined_to_namespace",
    "future_opus_run_confined_to_same_namespace_semantics",
    "all_mutable_sinks_namespaced_or_restored",
    "post_case_namespace_destroyed",
    "external_mutable_state_restored",
    "no_result_dependent_case_generation",
    "no_result_dependent_runtime_mutation",
]

for key in base_bool_keys:
    x = json.loads(json.dumps(iso_base))
    x["base"][key] = False
    assert iso.compile_isolation(x)["status"] == "FAIL_CLOSED", key

for key in case_bool_keys:
    x = json.loads(json.dumps(iso_base))
    x["cases"][0][key] = False
    assert iso.compile_isolation(x)["status"] == "FAIL_CLOSED", key

for mutation in ("prior", "namespace", "initial", "reset"):
    x = json.loads(json.dumps(iso_base))
    if mutation == "prior":
        x["cases"][1]["prior_case_ids_consumed"] = ["A"]
    elif mutation == "namespace":
        x["cases"][1]["mutable_namespace_sha256"] = B
    elif mutation == "initial":
        x["cases"][1]["opus_initial_state_sha256"] = C
    else:
        x["cases"][0]["post_reset_base_state_sha256"] = C
    assert iso.compile_isolation(x)["status"] == "FAIL_CLOSED", mutation

assert iso_gov["execution_authority"] is False
assert iso_gov["fresh_reality_authority"] is False
assert "NO_CURRENT_REAL_HARNESS_RECEIPTS_SATISFYING_THIS_CONTRACT" in iso_gov["hard_nonclaims"]

# Scope happy path with the authority-derived exact atom basis.
scope_base = {
    "schema": scope.INPUT_SCHEMA,
    "freeze": {
        "generator_content_addressed": True,
        "generator_frozen_before_case_exposure": True,
        "post_freeze_beacon_or_equivalent_precommitted_randomness": True,
        "case_count_fixed_before_first_result": True,
        "scorer_content_addressed": True,
        "brain_runtime_content_addressed": True,
        "tool_authority_content_addressed": True,
        "target_interface_content_addressed": True,
        "no_case_replacement_after_exposure": True,
        "no_adaptive_case_selection": True,
        "no_result_dependent_scope_edit": True,
        "generator_git_blob_sha": "a" * 40,
        "scorer_git_blob_sha": "b" * 40,
        "brain_commit_sha": "c" * 40,
        "tool_authority_sha256": "a" * 64,
        "target_interface_sha256": "b" * 64,
        "fixed_case_count": 1,
    },
    "cases": [
        {
            "case_id": "ALL",
            "case_payload_sha256": "c" * 64,
            "case_initial_state_sha256": "d" * 64,
            "coverage": {
                "independently_verified": True,
                "receipt_sha256": "e" * 64,
                "target_atoms": {pid: sorted(atoms) for pid, atoms in derived.items()},
            },
        }
    ],
}

scope_out = scope.compile_scope(scope_base)
assert scope_out["status"] == "PASS__FINITE_COMPLETE_CONTENT_ADDRESSED_MATCHED_SUCCESS_SCOPE"
assert scope_out["required_atom_count"] == 16
assert scope_out["coverage_complete"] is True

for key in [
    "generator_content_addressed",
    "generator_frozen_before_case_exposure",
    "post_freeze_beacon_or_equivalent_precommitted_randomness",
    "case_count_fixed_before_first_result",
    "scorer_content_addressed",
    "brain_runtime_content_addressed",
    "tool_authority_content_addressed",
    "target_interface_content_addressed",
    "no_case_replacement_after_exposure",
    "no_adaptive_case_selection",
    "no_result_dependent_scope_edit",
]:
    x = json.loads(json.dumps(scope_base))
    x["freeze"][key] = False
    assert scope.compile_scope(x)["status"] == "FAIL_CLOSED", key

# Missing and invented normalized atoms must fail.
for pid in sorted(TARGETS):
    x = json.loads(json.dumps(scope_base))
    x["cases"][0]["coverage"]["target_atoms"][pid].pop()
    assert scope.compile_scope(x)["status"] == "FAIL_CLOSED", ("missing", pid)

x = json.loads(json.dumps(scope_base))
x["cases"][0]["coverage"]["target_atoms"]["AGENCY_MATCHED_SUCCESS_NONINFERIOR"].append("dimension:invented")
assert scope.compile_scope(x)["status"] == "FAIL_CLOSED"

# Manifest digest must bind payload bytes/identity.
manifest = scope_out["case_manifest_sha256"]
x = json.loads(json.dumps(scope_base))
x["case_manifest_sha256"] = manifest
assert scope.compile_scope(x)["status"] == "PASS__FINITE_COMPLETE_CONTENT_ADDRESSED_MATCHED_SUCCESS_SCOPE"
x["cases"][0]["case_payload_sha256"] = "f" * 64
assert scope.compile_scope(x)["status"] == "FAIL_CLOSED"

assert scope_gov["execution_authority"] is False
assert scope_gov["fresh_reality_authority"] is False
assert "NO_CURRENT_CASE_MANIFEST_EXISTS" in scope_gov["hard_nonclaims"]

print(json.dumps({
    "status": "PASS",
    "verified_source_blobs": {str(p.relative_to(ROOT)): sha for p, sha in FILES.items()},
    "derived_target_count": len(derived),
    "derived_dimension_atom_count": sum(len(v) for v in derived.values()),
    "isolation_boolean_gates_adversarially_mutated": len(base_bool_keys) + len(case_bool_keys),
    "scope_freeze_gates_adversarially_mutated": 11,
    "authority_delta": 0
}, indent=2, sort_keys=True))
