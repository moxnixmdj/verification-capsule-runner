#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def require(cond, message):
    if not cond:
        raise AssertionError(message)


# Exact source identity from eight independently emitted chunk manifests.
expected_files = {}
source_heads = set()
for manifest_path in sorted(ROOT.glob("EXPECTED_BLOBS_CHUNK_*.json")):
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(doc["schema"] == "PR3514_BLOB_CHUNK_V1", "CHUNK_SCHEMA_INVALID")
    source_heads.add(doc["source_head_sha"])
    for rel, sha in doc["files"].items():
        require(rel not in expected_files, "DUPLICATE_EXPECTED_PATH:" + rel)
        expected_files[rel] = sha

require(source_heads == {"c2083e5d62f8221d08174490f41ac61c56102e7a"}, "SOURCE_HEAD_MISMATCH")
require(len(expected_files) == 65, "EXPECTED_PRIVATE_BLOB_COUNT_NOT_65")
for rel, sha in expected_files.items():
    p = ROOT / rel
    require(p.is_file(), "MISSING_EXACT_FILE:" + rel)
    require(git_blob_sha(p) == sha, "BLOB_MISMATCH:" + rel)


# Avoid importing untouched legacy route dependency trees. These stubs are inert
# and exist only to let the exact changed dispatcher module import. The actual
# 30 route runtime files still exist byte-for-byte for content-addressed checks.
runtime_pkg = importlib.import_module("canonical.runtime")

archive = types.ModuleType("canonical.runtime.raw_goal_archive_acceptance_v1")
class _NeverGrammar:
    def fullmatch(self, _goal):
        return None
archive.GRAMMAR = _NeverGrammar()

literal = types.ModuleType("canonical.runtime.raw_goal_exact_literal_acceptance_v1")
literal.preflight = lambda _goal: {"matched": False}

literal_json = types.ModuleType("canonical.runtime.raw_goal_literal_json_acceptance_v1")
literal_json.preflight = lambda _goal: {"matched": False}

legacy_v1 = types.ModuleType("canonical.runtime.r2_direct_end_to_end_adequacy_v1")
legacy_v1.run = lambda _request: {"pass": False, "status": "PUBLIC_CAPSULE_STUB_NOT_EXECUTED"}

for mod in (archive, literal, literal_json, legacy_v1):
    sys.modules[mod.__name__] = mod
    setattr(runtime_pkg, mod.__name__.rsplit(".", 1)[1], mod)

from canonical.runtime import r2_direct_route_registry_v1 as router
from canonical.runtime import r2_direct_route_live_integration_closure_v2 as closure
from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admission
from canonical.runtime import promote_r2_direct_route_v1 as promotion


# 1. Execute actual registry loading and 30-route authority join.
reg = router.load_registry(repo_root=ROOT)
require(reg["route_count"] == 30, "REGISTRY_COUNT_NOT_30")
state = router.effective_state(repo_root=ROOT)
require(state["baseline_activation_route_count"] == 30, "BASELINE_COUNT_NOT_30")
require(state["legacy_selection_metadata_count"] == 30, "LEGACY_METADATA_COUNT_NOT_30")
require(state["activation_auto_admitted_route_count"] == 0, "UNEXPECTED_ACTIVATION_AUTO_ADMISSION")
require(state["dynamic_admission_route_count"] == 0, "UNEXPECTED_DYNAMIC_ADMISSION")
require(state["deployable_route_count"] == 30, "DEPLOYABLE_COUNT_NOT_30")
require(state["stale_selection_metadata_route_ids"] == [], "STALE_SELECTION_METADATA")


# 2. Execute semantic-open stop-fallback behavior in exact dispatcher code.
WORLDSET = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1"
EFFECT = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_COMPOSITION_V1"
world = {
    "route_id": WORLDSET,
    "selection_class": router.LEGACY_SELECTION_CLASS,
    "priority": 0,
    "semantic_open_stops_fallback": True,
}
effect = {
    "route_id": EFFECT,
    "selection_class": router.LEGACY_SELECTION_CLASS,
    "priority": 1,
    "semantic_open_stops_fallback": False,
}
fake_state = {
    "rows": [world, effect],
    "deployable_route_ids": [WORLDSET, EFFECT],
    "baseline_activation_route_ids": [WORLDSET, EFFECT],
    "legacy_selection_metadata_route_ids": [WORLDSET, EFFECT],
    "activation_auto_admitted_route_ids": [],
    "dynamic_admission_route_ids": [],
    "dynamic_shadowed_by_baseline_route_ids": [],
    "auto_admitted_route_ids": [],
    "stale_selection_metadata_route_ids": [],
    "deployable_route_count": 2,
    "baseline_activation_route_count": 2,
    "legacy_selection_metadata_count": 2,
    "activation_auto_admitted_route_count": 0,
    "dynamic_admission_route_count": 0,
    "auto_admitted_route_count": 0,
    "current_activation_path": "x",
    "current_activation_git_blob_sha": "y",
    "dynamic_admission_target_path": "z",
    "dynamic_admission_target_git_blob_sha": "w",
}
calls = []
orig_effective = router.effective_state
orig_preflight_row = router._preflight_row
try:
    router.effective_state = lambda **_kw: fake_state
    def fake_pf(row, request, repo_root):
        calls.append(row["route_id"])
        if row["route_id"] == WORLDSET:
            return {
                "matched": False,
                "direct_route_semantic_open": True,
                "status": "OPEN__DECISION_CHANGING_WORLDSET",
                "route_id": WORLDSET,
            }
        return {"matched": True, "route_id": EFFECT}
    router._preflight_row = fake_pf
    sem = router.preflight({"task_id": "public-capsule", "goal": "g"}, repo_root=ROOT)
finally:
    router.effective_state = orig_effective
    router._preflight_row = orig_preflight_row

require(sem.get("direct_route_semantic_open") is True, "SEMANTIC_OPEN_NOT_PRESERVED")
require(sem.get("route_id") == WORLDSET, "SEMANTIC_OPEN_WRONG_ROUTE")
require(calls == [WORLDSET], "SEMANTIC_OPEN_FELL_THROUGH")


# 3. Execute new dynamic-route collision fail-closed behavior.
d1 = {
    "route_id": "DYNAMIC::A",
    "selection_class": router.DYNAMIC_SELECTION_CLASS,
    "activation_index": 30,
}
d2 = {
    "route_id": "DYNAMIC::B",
    "selection_class": router.DYNAMIC_SELECTION_CLASS,
    "activation_index": 31,
}
dyn_state = dict(fake_state)
dyn_state["rows"] = [d1, d2]
dyn_state["deployable_route_ids"] = ["DYNAMIC::A", "DYNAMIC::B"]
try:
    router.effective_state = lambda **_kw: dyn_state
    router._preflight_row = lambda row, request, repo_root: {
        "matched": True,
        "route_id": row["route_id"],
    }
    collision = router.preflight({"task_id": "public-capsule", "goal": "g"}, repo_root=ROOT)
finally:
    router.effective_state = orig_effective
    router._preflight_row = orig_preflight_row

require(collision["status"] == "FAIL_CLOSED__DIRECT_ROUTE_COLLISION", "DYNAMIC_COLLISION_NOT_FAIL_CLOSED")
require(collision["matching_route_ids"] == ["DYNAMIC::A", "DYNAMIC::B"], "DYNAMIC_COLLISION_IDS_WRONG")


# 4. Execute verified-deployable == default-executable closure gate.
closed = closure.evaluate(repo_root=ROOT)
require(closed["pass"] is True, "LIVE_INTEGRATION_CLOSURE_FAILED:" + json.dumps(closed, sort_keys=True))
require(closed["verified_deployable_equals_default_executable"] is True, "D_EQ_R_FAILED")
require(closed["expected_deployable_route_count"] == 30, "CLOSURE_EXPECTED_COUNT_NOT_30")
require(closed["effective_executable_route_count"] == 30, "CLOSURE_EXECUTABLE_COUNT_NOT_30")


# 5. Execute proof-carrying dynamic promotion and CURRENT-pointer replay.
with tempfile.TemporaryDirectory() as td:
    temp = Path(td)
    for rel in ("canonical/runtime", "canonical/governance", "canonical/verification"):
        (temp / rel).mkdir(parents=True, exist_ok=True)

    manifest_rel = "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_20261009_V1.json"
    pointer_rel = "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
    shutil.copyfile(ROOT / manifest_rel, temp / manifest_rel)
    shutil.copyfile(ROOT / pointer_rel, temp / pointer_rel)

    runtime_rel = "canonical/runtime/public_capsule_dynamic_route_v1.py"
    verify_rel = "canonical/verification/PUBLIC_CAPSULE_DYNAMIC_ROUTE_VERIFY_V1.json"
    candidate_rel = "canonical/governance/PUBLIC_CAPSULE_DYNAMIC_ROUTE_CANDIDATE_V1.json"
    receipt_rel = "canonical/verification/PUBLIC_CAPSULE_DYNAMIC_ROUTE_RECEIPT_V1.json"

    (temp / runtime_rel).write_text(
        "def preflight(request):\n    return {'matched': False}\n"
        "def run(request):\n    return {'pass': True}\n",
        encoding="utf-8",
    )
    (temp / verify_rel).write_text('{"status":"PUBLIC_CAPSULE_PASS"}\n', encoding="utf-8")

    candidate = {
        "schema": admission.CANDIDATE_SCHEMA,
        "route_id": "DIRECT_ADEQUACY::PUBLIC_CAPSULE_DYNAMIC_V1",
        "capability_id": "public.capsule.dynamic.v1",
        "deployment_requested": True,
        "selection_class": admission.SELECTION_CLASS,
        "runtime_path": runtime_rel,
        "runtime_git_blob_sha": admission.git_blob_sha(temp / runtime_rel),
        "preflight_callable": "preflight",
        "run_callable": "run",
        "route_verification_path": verify_rel,
        "route_verification_git_blob_sha": admission.git_blob_sha(temp / verify_rel),
        "scope": "PUBLIC_CAPSULE_SYNTHETIC_ONLY",
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }
    (temp / candidate_rel).write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidate_sha = admission.git_blob_sha(temp / candidate_rel)

    receipt = {
        "schema": admission.RECEIPT_SCHEMA,
        "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
        "candidate_path": candidate_rel,
        "candidate_git_blob_sha": candidate_sha,
        "route_id": candidate["route_id"],
        "runtime_path": runtime_rel,
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "route_verification_path": verify_rel,
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
    (temp / receipt_rel).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    promoted = promotion.promote(
        candidate_path=candidate_rel,
        receipt_path=receipt_rel,
        repo_root=temp,
        pointer_path=temp / pointer_rel,
    )
    require(promoted["pass"] is True, "PROMOTION_FAILED:" + json.dumps(promoted, sort_keys=True))
    require(promoted["frontier_changed"] is True, "PROMOTION_DID_NOT_CHANGE_FRONTIER")
    observed = admission.load_current_admissions(repo_root=temp, pointer_path=temp / pointer_rel)
    require(len(observed["admissions"]) == 1, "PROMOTION_NOT_RELOADED")
    require(observed["admissions"][0]["route_id"] == candidate["route_id"], "PROMOTED_ROUTE_ID_MISMATCH")

result = {
    "schema": "PROJECT_BRAIN_PR3514_R2_DEFAULT_LIVE_PUBLIC_EXECUTION_RECEIPT_V1",
    "status": "PASS__PUBLIC_CAPSULE_EXECUTED_CHANGED_DEFAULT_LIVE_INTEGRATION",
    "pass": True,
    "source_head_sha": next(iter(source_heads)),
    "exact_private_blob_count": len(expected_files),
    "baseline_route_count": 30,
    "effective_route_count": 30,
    "semantic_open_stop_fallback_verified": True,
    "dynamic_collision_fail_closed_verified": True,
    "verified_deployable_equals_default_executable": True,
    "synthetic_dynamic_promotion_pointer_replay_verified": True,
    "full_private_brain_end_to_end_replay_claimed": False,
    "terminal_authority": False,
}
print(json.dumps(result, indent=2, sort_keys=True))
