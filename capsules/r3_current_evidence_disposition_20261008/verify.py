from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "r3_improvement_queue_driver_v1.py"
compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec")

canonical = types.ModuleType("canonical")
runtime = types.ModuleType("canonical.runtime")
canonical.runtime = runtime
canonical.__path__ = []
runtime.__path__ = []
sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime

learning = types.ModuleType("canonical.runtime.autonomous_verified_self_improvement_v1")
learning.DEFAULT_STATE_PATH = HERE / "unused-state.json"

def load_state(path):
    p = Path(path)
    if not p.exists():
        return {
            "observations": {},
            "improvement_queue": {},
            "episodes": {},
            "skills": {},
            "stats": {},
        }
    return json.loads(p.read_text(encoding="utf-8"))

def write_state(state, path):
    Path(path).write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

def refresh_stats(state):
    q = state.setdefault("improvement_queue", {})
    state["stats"] = {
        "pending_improvement_count": sum(
            1 for x in q.values()
            if isinstance(x, dict) and x.get("status") == "PENDING"
        ),
        "parked_improvement_count": sum(
            1 for x in q.values()
            if isinstance(x, dict) and x.get("status") == "PARKED"
        ),
        "parked_success_learning_count": sum(
            1 for x in q.values()
            if (
                isinstance(x, dict)
                and x.get("status") == "PARKED"
                and x.get("kind") == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
            )
        ),
    }

def next_action(*, state_path):
    state = load_state(state_path)
    rows = [
        dict(x) for x in state.get("improvement_queue", {}).values()
        if isinstance(x, dict) and x.get("status") == "PENDING"
    ]
    if not rows:
        return None
    rows.sort(key=lambda x: (
        int(x.get("priority", 10**9)),
        -int(x.get("observations", 0)),
        str(x.get("work_id") or ""),
    ))
    return rows[0]

def record_attempt(work_id, *, status, reason, state_path):
    state = load_state(state_path)
    row = state["improvement_queue"][work_id]
    row["attempt_count"] = int(row.get("attempt_count", 0)) + 1
    row["last_attempt_observations"] = int(row.get("observations", 0))
    row["last_attempt_status"] = status
    row["last_attempt_reason"] = reason
    refresh_stats(state)
    write_state(state, state_path)

def replay_context(observation_id, *, state_path):
    state = load_state(state_path)
    row = state["observations"][observation_id]
    return {
        "observation_id": observation_id,
        "replay_capsule_sha256": row["replay_capsule_sha256"],
        "context": dict(row["replay_context"]),
        "replay_authorized": False,
    }

learning.load_state = load_state
learning._write_state = write_state
learning._refresh_stats = refresh_stats
learning.next_improvement_action = next_action
learning._record_improvement_attempt = record_attempt
learning.get_success_replay_context = replay_context
runtime.autonomous_verified_self_improvement_v1 = learning
sys.modules[learning.__name__] = learning

auth = types.ModuleType("canonical.runtime.executable_skill_verification_authenticator_v1")
auth.authenticate_and_verify = lambda *a, **k: {"pass": False, "reason": "unused"}
sys.modules[auth.__name__] = auth

independent = types.ModuleType("canonical.runtime.r3_independent_learning_verifier_v1")
independent.verify_episode_request = lambda *a, **k: None
independent.verify_skill_request = lambda *a, **k: None
runtime.r3_independent_learning_verifier_v1 = independent
sys.modules[independent.__name__] = independent

adapter = types.ModuleType("canonical.runtime.r3_bound_success_adapter_v1")
adapter.calls = 0
def no_candidate(request, *, repo_root):
    adapter.calls += 1
    return None
adapter.adapt = no_candidate
runtime.r3_bound_success_adapter_v1 = adapter
sys.modules[adapter.__name__] = adapter

spec = importlib.util.spec_from_file_location("capsule_driver", SOURCE)
driver = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(driver)

def make_frontier(root: Path, suffix: str = "a"):
    for rel in driver.SUCCESS_LEARNING_FRONTIER_PATHS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel + ":" + suffix, encoding="utf-8")

def make_state(path: Path):
    oid = "observation:opaque"
    wid = "work:opaque"
    state = {
        "observations": {
            oid: {
                "observation_id": oid,
                "surface": "OPAQUE_EXTERNAL_SURFACE",
                "schema": "TEST_SUCCESS_V1",
                "replay_capsule_sha256": "r" * 64,
                "replay_context": {
                    "mode": "generic",
                    "problem": {"task_id": "opaque"},
                },
            }
        },
        "improvement_queue": {
            wid: {
                "work_id": wid,
                "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
                "priority": 50,
                "identity": {
                    "surface": "OPAQUE_EXTERNAL_SURFACE",
                    "schema": "TEST_SUCCESS_V1",
                },
                "payload": {
                    "observation_id": oid,
                    "required_result": "VERIFIED_EPISODE_OR_PROVED_NONLEARNABLE_SUCCESS",
                },
                "status": "PENDING",
                "observations": 1,
                "reopen_count": 0,
                "attempt_count": 0,
                "last_attempt_observations": None,
                "last_attempt_status": None,
                "last_attempt_reason": None,
            }
        },
        "episodes": {},
        "skills": {},
        "stats": {},
    }
    refresh_stats(state)
    write_state(state, path)
    return oid, wid

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    make_frontier(root, "a")
    state_path = root / "state.json"
    oid, wid = make_state(state_path)

    first = driver.advance_once(state_path=state_path, repo_root=root)
    assert first["pass"] is True, first
    assert first["progress"] is False, first
    assert first["disposition_recorded"] is True, first
    assert first["permanent_nonlearnability_claimed"] is False, first
    assert first["status"] == (
        "IMPROVEMENT_PARKED__"
        "PROVED_NONLEARNABLE_FROM_CURRENT_RETAINED_EVIDENCE"
    ), first
    state = load_state(state_path)
    assert state["improvement_queue"][wid]["status"] == "PARKED", state
    assert state["stats"]["parked_success_learning_count"] == 1, state
    obs = state["observations"][oid]
    assert obs["learning_disposition"] == (
        "PROVED_NONLEARNABLE_FROM_CURRENT_RETAINED_EVIDENCE"
    ), obs
    assert obs["permanent_nonlearnability_claimed"] is False, obs
    frontier_a = first["verification_frontier_sha256"]
    assert adapter.calls == 1, adapter.calls

    same = driver.advance_once(state_path=state_path, repo_root=root)
    assert same["status"] == "IMPROVEMENT_QUEUE_EMPTY", same
    assert adapter.calls == 1, adapter.calls

    changed = root / driver.SUCCESS_LEARNING_FRONTIER_PATHS[0]
    changed.write_text(changed.read_text(encoding="utf-8") + ":changed", encoding="utf-8")
    after_change = driver.advance_once(state_path=state_path, repo_root=root)
    assert after_change["disposition_recorded"] is True, after_change
    assert after_change["verification_frontier_sha256"] != frontier_a, after_change
    assert adapter.calls == 2, adapter.calls
    state = load_state(state_path)
    assert state["improvement_queue"][wid]["reopen_count"] == 1, state
    assert state["improvement_queue"][wid]["status"] == "PARKED", state

    external_calls = []
    def external_adapter(request):
        external_calls.append(request["kind"])
        return None
    external = driver.advance_once(
        state_path=state_path,
        repo_root=root,
        episode_verification_provider=lambda request: None,
        success_episode_adapter_provider=external_adapter,
    )
    assert external["pass"] is False, external
    assert external["attempt_backoff_recorded"] is True, external
    assert external_calls == ["SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE"], external_calls
    state = load_state(state_path)
    assert state["improvement_queue"][wid]["status"] == "PENDING", state
    assert state["improvement_queue"][wid]["reactivated_by"] == (
        "EXTERNAL_VERIFICATION_AUTHORITY_AVAILABLE"
    ), state
    assert state["improvement_queue"][wid]["reopen_count"] == 2, state

sequence = iter([
    {
        "schema": driver.SCHEMA,
        "status": "IMPROVEMENT_PARKED__PROVED_NONLEARNABLE_FROM_CURRENT_RETAINED_EVIDENCE",
        "pass": True,
        "progress": False,
        "disposition_recorded": True,
        "terminal_authority": False,
    },
    {
        "schema": driver.SCHEMA,
        "status": "IMPROVEMENT_ADVANCED__EPISODE_VERIFIED",
        "pass": True,
        "progress": True,
        "terminal_authority": False,
    },
    {
        "schema": driver.SCHEMA,
        "status": "IMPROVEMENT_QUEUE_STABLE",
        "pass": True,
        "progress": False,
        "terminal_authority": False,
    },
])
original_advance = driver.advance_once
driver.advance_once = lambda **kwargs: next(sequence)
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    make_frontier(root)
    state_path = root / "state.json"
    write_state({
        "observations": {},
        "improvement_queue": {},
        "episodes": {},
        "skills": {},
        "stats": {},
    }, state_path)
    drained = driver.drain(
        state_path=state_path,
        repo_root=root,
        max_actions=3,
    )
driver.advance_once = original_advance
assert len(drained["actions"]) == 3, drained
assert drained["progress_count"] == 1, drained
assert drained["status"] == "IMPROVEMENT_QUEUE_ADVANCED", drained

print(json.dumps({
    "status": "PASS",
    "verified": [
        "exact_current_source_compile",
        "unsupported_default_success_parks_current_evidence",
        "unchanged_frontier_no_retry",
        "owned_frontier_change_reopens",
        "external_authority_reopens",
        "no_permanent_nonlearnability_claim",
        "parked_disposition_does_not_starve_downstream_work"
    ]
}, sort_keys=True))
