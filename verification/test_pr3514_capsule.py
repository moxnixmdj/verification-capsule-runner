#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
CANON = ROOT / "canonical"
RUNTIME = CANON / "runtime"
GOV = CANON / "governance"
VER = CANON / "verification"

EXPECTED_SOURCE_BLOBS = {
    "canonical/runtime/r2_direct_route_registry_v1.py": "151641160bb6623a89e2584f2b3cd5cb62050bd4",
    "canonical/runtime/r2_direct_route_dynamic_admission_v1.py": "65fc5bdb5283944d058c6c6a2ff1fe360aa17489",
    "canonical/runtime/promote_r2_direct_route_v1.py": "85be8711c55243a8355094d766ced625a30062c7",
}

def blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def blob(path: Path) -> str:
    return blob_bytes(path.read_bytes())

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def write_json(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")

def assert_eq(a, b, label):
    if a != b:
        raise AssertionError(f"{label}: {a!r} != {b!r}")

def assert_true(v, label):
    if not v:
        raise AssertionError(label)

# 1) Exact-byte binding to the private PR implementation.
for rel, expected in EXPECTED_SOURCE_BLOBS.items():
    actual = blob(ROOT / rel)
    assert_eq(actual, expected, "source blob mismatch " + rel)

# Package scaffolding + direct import dependencies.
write(CANON / "__init__.py", "")
write(RUNTIME / "__init__.py", "")
write(
    RUNTIME / "raw_goal_archive_acceptance_v1.py",
    "import re\nGRAMMAR = re.compile(r'NEVER_MATCH_ARCHIVE(?P<manifest>x)(?P<output>y)')\n",
)
write(
    RUNTIME / "raw_goal_exact_literal_acceptance_v1.py",
    "def preflight(goal):\n    return {'matched': False}\n",
)
write(
    RUNTIME / "raw_goal_literal_json_acceptance_v1.py",
    "def preflight(goal):\n    return {'matched': False}\n",
)

route_a = """def preflight(request, repo_root=None):
    g = str(request.get('goal') or '')
    if g == 'open':
        return {'matched': False, 'direct_route_semantic_open': True, 'route_id': 'LEGACY_A', 'status': 'OPEN__A'}
    return {'matched': False, 'route_id': 'LEGACY_A'}

def run(request, repo_root=None):
    return {'pass': True, 'route_id': 'LEGACY_A', 'status': 'PASS_A'}
"""
route_b = """def preflight(request, repo_root=None):
    g = str(request.get('goal') or '')
    if g == 'open':
        raise RuntimeError('B_MUST_NOT_RUN_AFTER_A_SEMANTIC_OPEN')
    return {'matched': g in {'b', 'overlap'}, 'route_id': 'LEGACY_B'}

def run(request, repo_root=None):
    return {'pass': True, 'route_id': 'LEGACY_B', 'status': 'PASS_B'}
"""
route_c = """def preflight(request, repo_root=None):
    g = str(request.get('goal') or '')
    return {'matched': g in {'c', 'overlap'}, 'route_id': 'DYNAMIC_C'}

def run(request, repo_root=None):
    return {'pass': True, 'route_id': 'DYNAMIC_C', 'status': 'PASS_C'}
"""
write(RUNTIME / "stub_route_a.py", route_a)
write(RUNTIME / "stub_route_b.py", route_b)
write(RUNTIME / "stub_route_c.py", route_c)
write_json(VER / "stub_a_verify.json", {"status": "PASS_A"})
write_json(VER / "stub_b_verify.json", {"status": "PASS_B"})
write_json(VER / "stub_c_verify.json", {"status": "PASS_C"})

rows = [
    {
        "route_id": "LEGACY_A",
        "priority": 0,
        "active": True,
        "runtime_path": "canonical/runtime/stub_route_a.py",
        "runtime_git_blob_sha": blob(RUNTIME / "stub_route_a.py"),
        "preflight_callable": "preflight",
        "run_callable": "run",
        "verification_path": "canonical/verification/stub_a_verify.json",
        "verification_git_blob_sha": blob(VER / "stub_a_verify.json"),
        "selection_class": "LEGACY_ORDERED_MIGRATION",
        "semantic_open_stops_fallback": True,
    },
    {
        "route_id": "LEGACY_B",
        "priority": 1,
        "active": True,
        "runtime_path": "canonical/runtime/stub_route_b.py",
        "runtime_git_blob_sha": blob(RUNTIME / "stub_route_b.py"),
        "preflight_callable": "preflight",
        "run_callable": "run",
        "verification_path": "canonical/verification/stub_b_verify.json",
        "verification_git_blob_sha": blob(VER / "stub_b_verify.json"),
        "selection_class": "LEGACY_ORDERED_MIGRATION",
        "semantic_open_stops_fallback": False,
    },
]
registry = {
    "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_V1",
    "status": "ACTIVE_SYNTHETIC_CAPSULE",
    "selection_role": "LEGACY_PRECEDENCE_OVERLAY_ONLY__CURRENT_R2_ACTIVATION_IS_DEPLOYABLE_ROUTE_UNIVERSE",
    "route_count": 2,
    "routes": rows,
}
reg_path = GOV / "R2_DIRECT_ROUTE_REGISTRY_CAPSULE_V1.json"
write_json(reg_path, registry)
write_json(
    GOV / "CURRENT_R2_DIRECT_ROUTE_REGISTRY.json",
    {
        "schema": "PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_REGISTRY_V1",
        "status": "ACTIVE_CURRENT_R2_DIRECT_ROUTE_SELECTION_METADATA_POINTER",
        "binding_semantics": "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
        "target": {
            "path": "canonical/governance/R2_DIRECT_ROUTE_REGISTRY_CAPSULE_V1.json",
            "git_blob_sha": blob(reg_path),
            "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_V1",
        },
    },
)

activation = {
    "schema": "CAPSULE_ACTIVATION_V1",
    "current_routes": [
        {
            "route_id": r["route_id"],
            "runtime": r["runtime_path"],
            "runtime_git_blob_sha": r["runtime_git_blob_sha"],
            "verification": {
                "path": r["verification_path"],
                "git_blob_sha": r["verification_git_blob_sha"],
            },
        }
        for r in rows
    ],
}
act_path = GOV / "R2_DIRECT_ACTIVATION_CAPSULE_V1.json"
write_json(act_path, activation)
write_json(
    GOV / "CURRENT_R2_DECISION_INTELLIGENCE.json",
    {
        "direct_adequacy": {
            "activation_path": "canonical/governance/R2_DIRECT_ACTIVATION_CAPSULE_V1.json",
            "activation_git_blob_sha": blob(act_path),
            "current_route_count": 2,
        }
    },
)

empty_manifest = {
    "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
    "status": "ACTIVE_DYNAMIC_ADMISSIONS__EMPTY",
    "selection_class": "UNIQUE_MATCH_REQUIRED",
    "collision_policy": "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
    "admission_count": 0,
    "admissions": [],
}
empty_path = GOV / "R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_CAPSULE_EMPTY.json"
write_json(empty_path, empty_manifest)
write_json(
    GOV / "CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json",
    {
        "schema": "PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_POINTER_V1",
        "date": "2026-10-09",
        "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
        "binding_semantics": "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
        "target": {
            "path": "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_CAPSULE_EMPTY.json",
            "git_blob_sha": blob(empty_path),
            "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
        },
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    },
)

sys.path.insert(0, str(ROOT))
dispatcher = importlib.import_module("canonical.runtime.r2_direct_route_registry_v1")
admission = importlib.import_module("canonical.runtime.r2_direct_route_dynamic_admission_v1")
promoter = importlib.import_module("canonical.runtime.promote_r2_direct_route_v1")

# 2) Exact legacy behavior: precedence and semantic-open barrier.
cat = dispatcher.catalog(repo_root=ROOT)
assert_eq(cat["route_count"], 2, "baseline route count")
assert_eq(dispatcher.preflight({"task_id":"t","goal":"open"}, repo_root=ROOT)["status"], "OPEN__A", "semantic-open barrier")
pf_b = dispatcher.preflight({"task_id":"t","goal":"b"}, repo_root=ROOT)
assert_eq(pf_b["route_id"], "LEGACY_B", "legacy B selected")
run_b = dispatcher.run({"task_id":"t","goal":"b"}, repo_root=ROOT)
assert_true(run_b["pass"], "legacy B run")
assert_eq(run_b["status"], "PASS_B", "legacy B status")

# 3) Build independently-bound deployment candidate + receipt for DYNAMIC_C.
candidate = {
    "schema": admission.CANDIDATE_SCHEMA,
    "route_id": "DYNAMIC_C",
    "capability_id": "capsule.dynamic.c",
    "runtime_path": "canonical/runtime/stub_route_c.py",
    "runtime_git_blob_sha": blob(RUNTIME / "stub_route_c.py"),
    "preflight_callable": "preflight",
    "run_callable": "run",
    "route_verification_path": "canonical/verification/stub_c_verify.json",
    "route_verification_git_blob_sha": blob(VER / "stub_c_verify.json"),
    "scope": "capsule://dynamic-c",
    "selection_class": admission.SELECTION_CLASS,
    "deployment_requested": True,
    "incremental_spend_usd": 0,
    "terminal_authority": False,
}
cand_path = GOV / "DYNAMIC_C_CANDIDATE.json"
write_json(cand_path, candidate)
cand_sha = blob(cand_path)
receipt = {
    "schema": admission.RECEIPT_SCHEMA,
    "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
    "candidate_path": "canonical/governance/DYNAMIC_C_CANDIDATE.json",
    "candidate_git_blob_sha": cand_sha,
    "route_id": "DYNAMIC_C",
    "runtime_path": candidate["runtime_path"],
    "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
    "route_verification_path": candidate["route_verification_path"],
    "route_verification_git_blob_sha": candidate["route_verification_git_blob_sha"],
    "selection_class": admission.SELECTION_CLASS,
    "independent_verified": True,
    "preflight_pure_no_effect": True,
    "matched_route_failure_no_fallthrough": True,
    "producer_independent_acceptance": True,
    "exact_raw_obligation_acceptance": True,
    "deployment_eligible": True,
    "verification_authority_mutated": False,
    "promotion_authority": False,
    "terminal_authority": False,
    "incremental_spend_usd": 0,
}
receipt_path = VER / "DYNAMIC_C_RECEIPT.json"
write_json(receipt_path, receipt)

# 4) Atomic promotion -> current pointer replay.
out = promoter.promote(
    candidate_path="canonical/governance/DYNAMIC_C_CANDIDATE.json",
    receipt_path="canonical/verification/DYNAMIC_C_RECEIPT.json",
    repo_root=ROOT,
)
assert_true(out["pass"], "promotion pass")
assert_true(out["frontier_changed"], "promotion frontier changed")
assert_eq(out["status"], "PASS__R2_DIRECT_ROUTE_PROMOTED_AND_CURRENT_POINTER_REPLAYED", "promotion status")
loaded = admission.load_current_admissions(repo_root=ROOT)
assert_eq([x["route_id"] for x in loaded["admissions"]], ["DYNAMIC_C"], "current admission contains C")

# 5) New route becomes live without source edit; unique match executes.
state = dispatcher.effective_state(repo_root=ROOT)
assert_eq(state["dynamic_admission_route_ids"], ["DYNAMIC_C"], "dynamic route joined")
pf_c = dispatcher.preflight({"task_id":"t","goal":"c"}, repo_root=ROOT)
assert_eq(pf_c["route_id"], "DYNAMIC_C", "dynamic C selected")
run_c = dispatcher.run({"task_id":"t","goal":"c"}, repo_root=ROOT)
assert_true(run_c["pass"], "dynamic C run")
assert_eq(run_c["status"], "PASS_C", "dynamic C status")

# 6) Dynamic/legacy overlap fails closed, never silently prioritizes.
collision = dispatcher.preflight({"task_id":"t","goal":"overlap"}, repo_root=ROOT)
assert_eq(collision["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION", "overlap fail closed")
assert_eq(collision["reason"], "AUTO_ADMITTED_ROUTE_OVERLAPS_LEGACY_ROUTE", "overlap reason")
assert_eq(sorted(collision["matching_route_ids"]), ["DYNAMIC_C", "LEGACY_B"], "collision ids")

# 7) Idempotent replay is non-mutating.
out2 = promoter.promote(
    candidate_path="canonical/governance/DYNAMIC_C_CANDIDATE.json",
    receipt_path="canonical/verification/DYNAMIC_C_RECEIPT.json",
    repo_root=ROOT,
)
assert_true(out2["pass"], "idempotent replay pass")
assert_true(out2["frontier_changed"] is False, "idempotent replay no frontier change")
assert_eq(out2["status"], "ALREADY_LIVE_EXACT_BINDING", "idempotent replay status")

print(json.dumps({
    "status": "PASS__PR3514_PUBLIC_ISOLATED_EXECUTION_CAPSULE",
    "source_blobs": EXPECTED_SOURCE_BLOBS,
    "legacy_route_count": 2,
    "dynamic_promoted": "DYNAMIC_C",
    "semantic_open_barrier_verified": True,
    "dynamic_unique_execution_verified": True,
    "dynamic_legacy_collision_fail_closed_verified": True,
    "idempotent_promotion_replay_verified": True,
    "terminal_authority": False,
    "full_private_brain_integration_verified": False,
}, indent=2, sort_keys=True))
