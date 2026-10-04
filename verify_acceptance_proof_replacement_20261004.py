from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "proof_replacement_v1_20261004"
PLANNER = SUB / "acceptance_proof_replacement_planner_v1.py"
PROOF = SUB / "proof_obligation_delta_compiler_v1.py"
SCOPE = SUB / "protocol_implication_scope_algebra_v2.py"

EXPECTED_PLANNER = "ebd9c74ef1b7dcbabd60a3368f6e070ed1e21df6"
EXPECTED_PROOF = "dea41dc780c92efdd7c8b4b8551129197ab8cca8"
EXPECTED_SCOPE = "6aba64c26433b4a8646d5d96bb07e5ba5b46ca1b"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

assert git_blob_sha(PLANNER) == EXPECTED_PLANNER
assert git_blob_sha(PROOF) == EXPECTED_PROOF
assert git_blob_sha(SCOPE) == EXPECTED_SCOPE

canonical = types.ModuleType("canonical")
runtime_pkg = types.ModuleType("canonical.runtime")
canonical.runtime = runtime_pkg
sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime_pkg

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

proof = load("canonical.runtime.proof_obligation_delta_compiler_v1", PROOF)
scope = load("canonical.runtime.protocol_implication_scope_algebra_v2", SCOPE)
planner = load("canonical.runtime.acceptance_proof_replacement_planner_v1", PLANNER)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40

def receipt(path: str, sha: str = SHA_A):
    return {"path": path, "git_blob_sha": sha}

def base_doc():
    return {
        "schema": planner.INPUT_SCHEMA,
        "target": {
            "id": "P",
            "scope_ref": "scope:P",
            "receipt": receipt("canonical/governance/target.json"),
        },
        "allow_fresh_reality": False,
        "route_candidates": [],
    }

def delta_payload():
    return {
        "schema": proof.INPUT_SCHEMA,
        "target": {
            "id": "P",
            "scope_components": [
                {"id": "scope", "source_path": "target.json", "source_sha": SHA_A},
            ],
            "required_atoms": ["A"],
            "required_invariants": ["I"],
            "metric_requirements": [
                {"metric": "score", "direction": "higher", "threshold": 1.0},
            ],
        },
        "witness": {
            "id": "W",
            "scope_components": [
                {"id": "w_scope", "source_path": "witness.json", "source_sha": SHA_B},
            ],
            "proved_atoms": ["WA"],
            "proved_invariants": ["WI"],
            "metric_bounds": {"w_score": {"lower": 1.0}},
        },
        "scope_bindings": [
            {
                "witness_component": "w_scope",
                "target_component": "scope",
                "relation": "EXACT",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/scope.json", SHA_C),
            }
        ],
        "atom_bindings": [
            {
                "witness_atom": "WA",
                "target_atom": "A",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/atom.json", SHA_C),
            }
        ],
        "invariant_bindings": [
            {
                "witness_invariant": "WI",
                "target_invariant": "I",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/invariant.json", SHA_C),
            }
        ],
        "metric_bindings": [
            {
                "witness_metric": "w_score",
                "target_metric": "score",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/metric.json", SHA_C),
            }
        ],
    }

def implication_payload():
    return {
        "target": {
            "scope_ref": "scope:P",
            "required_atoms": ["A"],
            "metric_requirements": [
                {"metric": "score", "direction": "higher", "threshold": 1.0},
            ],
        },
        "witness": {
            "scope_ref": "scope:W",
            "proved_atoms": ["A"],
            "metric_bounds": {"score": {"lower": 1.0}},
            "verified": True,
            "independent": True,
            "contamination_clean": True,
        },
        "verified_scope_relations": [
            {
                "witness_scope": "scope:W",
                "target_scope": "scope:P",
                "relation": "SUPERSET",
                "verified": True,
                "independent": True,
                "receipt": "canonical/verification/scope-relation.json@" + SHA_C,
            }
        ],
        "verified_implications": [],
    }

def assert_zero_authority(out):
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert out["new_reality_units_consumed"] == 0

# Positive exact-binding route may become only a zero-credit replacement candidate.
d = base_doc()
d["route_candidates"] = [{
    "route_id": "ceiling",
    "kind": "OBJECTIVE_CEILING",
    "mode": "DELTA",
    "zero_reality": True,
    "critical_path_seconds": 2,
    "payload": delta_payload(),
}]
out = planner.compile_replacement_frontier(d)
assert out["status"] == "PROVED_REPLACEMENT_CANDIDATE_FOUND__ZERO_CREDIT"
assert out["closure_candidates"][0]["route_id"] == "ceiling"
assert_zero_authority(out)

# Scope-safe implication route can pass only with explicit verified superset relation.
d = base_doc()
d["route_candidates"] = [{
    "route_id": "formal",
    "kind": "FORMAL_IMPLICATION",
    "mode": "IMPLICATION",
    "zero_reality": True,
    "critical_path_seconds": 1,
    "payload": implication_payload(),
}]
out = planner.compile_replacement_frontier(d)
assert out["closure_candidates"][0]["proof_status"] == "PASS"
assert_zero_authority(out)

# Name similarity / atom spelling alone can never replace explicit binding.
d = base_doc()
p = delta_payload()
p["witness"]["proved_atoms"] = ["A"]
p["atom_bindings"] = []
d["route_candidates"] = [{
    "route_id": "name-only",
    "kind": "FORMAL_IMPLICATION",
    "mode": "DELTA",
    "zero_reality": True,
    "critical_path_seconds": 1,
    "payload": p,
}]
out = planner.compile_replacement_frontier(d)
assert out["closure_candidates"] == []
assert out["zero_reality_attempt_frontier"][0]["status"] == "PROOF_ATTEMPT_RESIDUAL_OPEN"
assert_zero_authority(out)

# Missing scope binding remains open even if atoms/metrics are otherwise perfect.
d = base_doc()
p = delta_payload()
p["scope_bindings"] = []
d["route_candidates"] = [{
    "route_id": "missing-scope",
    "kind": "VERIFIED_SCOPE_SUPERSET",
    "mode": "DELTA",
    "zero_reality": True,
    "critical_path_seconds": 1,
    "payload": p,
}]
out = planner.compile_replacement_frontier(d)
assert out["closure_candidates"] == []
assert out["zero_reality_attempt_frontier"][0]["proof_verdict"]["residual"]["missing_scope_components"] == ["scope"]
assert_zero_authority(out)

# Fresh empirical routes remain blocked by default.
d = base_doc()
d["route_candidates"] = [{
    "route_id": "empirical",
    "kind": "MATCHED_EMPIRICAL",
    "mode": "UNPROVED",
    "zero_reality": False,
    "critical_path_seconds": 1,
}]
out = planner.compile_replacement_frontier(d)
assert out["zero_reality_attempt_frontier"] == []
assert out["blocked_fresh_reality_routes"][0]["route_id"] == "empirical"
assert_zero_authority(out)

# Target identity drift is a hard failure, never a residual.
d = base_doc()
p = delta_payload()
p["target"]["id"] = "OTHER"
d["route_candidates"] = [{
    "route_id": "drift",
    "kind": "OBJECTIVE_CEILING",
    "mode": "DELTA",
    "zero_reality": True,
    "critical_path_seconds": 1,
    "payload": p,
}]
out = planner.compile_replacement_frontier(d)
assert out["status"] == "FAIL_CLOSED"
assert "ROUTE_TARGET_IDENTITY_MISMATCH:drift" in out["errors"]
assert_zero_authority(out)

# Target itself must be content-addressed.
d = base_doc()
d["target"]["receipt"] = {"path": "target.json", "git_blob_sha": "bad"}
out = planner.compile_replacement_frontier(d)
assert out["status"] == "FAIL_CLOSED"
assert "TARGET_RECEIPT_NOT_CONTENT_ADDRESSED" in out["errors"]
assert_zero_authority(out)

# Precedence is proof-semantic, not merely shortest-duration-first.
d = base_doc()
d["route_candidates"] = [
    {
        "route_id": "metamorphic",
        "kind": "METAMORPHIC_INVARIANT",
        "mode": "UNPROVED",
        "zero_reality": True,
        "critical_path_seconds": 1,
    },
    {
        "route_id": "formal",
        "kind": "FORMAL_IMPLICATION",
        "mode": "UNPROVED",
        "zero_reality": True,
        "critical_path_seconds": 100,
    },
]
out = planner.compile_replacement_frontier(d)
assert [x["route_id"] for x in out["zero_reality_attempt_frontier"]] == ["formal", "metamorphic"]
assert_zero_authority(out)

print(json.dumps({
    "status": "PASS",
    "planner_git_blob_sha": EXPECTED_PLANNER,
    "proof_dependency_git_blob_sha": EXPECTED_PROOF,
    "scope_dependency_git_blob_sha": EXPECTED_SCOPE,
    "target_drift_fails_closed": True,
    "name_similarity_grants_no_credit": True,
    "missing_scope_remains_open": True,
    "fresh_empirical_route_blocked_without_authority": True,
    "closure_candidate_is_zero_credit": True,
    "execution_authority": False,
    "promotion_authority": False,
    "fresh_reality_authority": False,
}, sort_keys=True))

# Additive predicate-local verifier; import executes its fail-closed checks.
import verify_livebench_if_acceptance_reduction_20261004
