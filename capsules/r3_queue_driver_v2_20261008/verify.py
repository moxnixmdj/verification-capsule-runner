from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "r3_improvement_queue_driver_v1.py"
compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec")

canonical = types.ModuleType("canonical")
runtime = types.ModuleType("canonical.runtime")
canonical.runtime = runtime
canonical.__path__ = []
runtime.__path__ = []
sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime

learning = types.ModuleType("canonical.runtime.autonomous_verified_self_improvement_v1")
learning.DEFAULT_STATE_PATH = ROOT / "unused-state.json"
learning.VERIFIED_SUPERSET_SCOPE_PREDICATE = "STRUCTURAL_MATCH_V1"

def load_state(path):
    p = Path(path)
    if not p.exists():
        return {"episodes": {}, "skills": {}, "improvement_queue": {}, "stats": {}}
    return json.loads(p.read_text(encoding="utf-8"))

def write_state(state, path):
    Path(path).write_text(json.dumps(state), encoding="utf-8")

def refresh_stats(state):
    q = state.setdefault("improvement_queue", {})
    state.setdefault("stats", {})["pending_improvement_count"] = sum(
        1 for x in q.values() if isinstance(x, dict) and x.get("status") == "PENDING"
    )

def next_action(*, state_path):
    rows = [
        x for x in load_state(state_path).get("improvement_queue", {}).values()
        if isinstance(x, dict) and x.get("status") == "PENDING"
    ]
    if not rows:
        return None
    return sorted(rows, key=lambda x: (x.get("priority", 10**9), -x.get("observations", 0), x.get("work_id", "")))[0]

def record_attempt(work_id, *, status, reason, state_path):
    state = load_state(state_path)
    row = state["improvement_queue"][work_id]
    row["attempt_count"] = int(row.get("attempt_count", 0)) + 1
    row["last_attempt_observations"] = int(row.get("observations", 0))
    row["last_attempt_status"] = status
    row["last_attempt_reason"] = reason
    refresh_stats(state)
    write_state(state, state_path)

def integrate_solver_output(out, *, state_path, **kwargs):
    state = load_state(state_path)
    cand = out.get("skill_candidate") or {}
    digest = cand.get("candidate_sha256")
    for row in state.get("improvement_queue", {}).values():
        if (
            isinstance(row, dict)
            and row.get("kind") == "VERIFY_SKILL_CANDIDATE"
            and (row.get("identity") or {}).get("candidate_sha256") == digest
        ):
            row["status"] = "RESOLVED"
            row["resolved_by"] = "stub-verified-skill"
    refresh_stats(state)
    write_state(state, state_path)
    return {"status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE", "pass": True}

learning.load_state = load_state
learning._write_state = write_state
learning._refresh_stats = refresh_stats
learning.next_improvement_action = next_action
learning._record_improvement_attempt = record_attempt
learning.integrate_solver_output = integrate_solver_output
learning._post_execution_independent_verification = lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected episode verification"))
learning.get_success_replay_context = lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected success replay"))
learning._candidate_from_verified_skill = lambda x: dict(x)
runtime.autonomous_verified_self_improvement_v1 = learning
sys.modules[learning.__name__] = learning

auth = types.ModuleType("canonical.runtime.executable_skill_verification_authenticator_v1")
auth.authenticate_and_verify = lambda *a, **k: {"pass": False, "reason": "default reject"}
sys.modules[auth.__name__] = auth

spec = importlib.util.spec_from_file_location("capsule_driver_v2", SOURCE)
driver = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(driver)

def make_state(path, queue):
    state = {"episodes": {}, "skills": {}, "improvement_queue": queue, "stats": {}}
    refresh_stats(state)
    write_state(state, path)

def work(work_id, kind, priority, payload=None, identity=None, observations=1):
    return {
        "work_id": work_id,
        "kind": kind,
        "priority": priority,
        "identity": identity or {},
        "payload": payload or {},
        "status": "PENDING",
        "observations": observations,
        "reopen_count": 0,
        "attempt_count": 0,
        "last_attempt_observations": None,
        "last_attempt_status": None,
        "last_attempt_reason": None,
    }

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "state.json"
    candidate = {"candidate_sha256": "sha256:c1", "candidate_only": True}
    make_state(path, {
        "skill": work(
            "skill", "VERIFY_SKILL_CANDIDATE", 10,
            payload={"candidate": candidate},
            identity={"candidate_sha256": "sha256:c1"},
        )
    })
    calls = []
    def provider(req):
        calls.append(req["kind"])
        return {"receipt": {"path": "r"}, "verification": {"path": "v"}}
    driver.authenticate_skill_verification = lambda *a, **k: {"pass": False, "reason": "independent rejection"}
    first = driver.advance_once(state_path=path, skill_verification_provider=provider)
    second = driver.advance_once(state_path=path, skill_verification_provider=provider)
    assert first["pass"] is False and first["attempt_backoff_recorded"] is True, first
    assert second["pass"] is True and second["progress"] is False, second
    assert second["blockers"][0]["blocker"] == "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE", second
    assert calls == ["SKILL_VERIFICATION"], calls
    state = load_state(path)
    assert state["improvement_queue"]["skill"]["attempt_count"] == 1
    assert state["improvement_queue"]["skill"]["last_attempt_observations"] == 1
    state["improvement_queue"]["skill"]["observations"] = 2
    write_state(state, path)
    third = driver.advance_once(state_path=path, skill_verification_provider=provider)
    assert third["pass"] is False and third["attempt_backoff_recorded"] is True, third
    assert calls == ["SKILL_VERIFICATION", "SKILL_VERIFICATION"], calls

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "state.json"
    candidate = {"candidate_sha256": "sha256:c2", "candidate_only": True}
    make_state(path, {
        "repair": work(
            "repair", "REPAIR_FAILURE_CLASS", 10,
            payload={"failure_fingerprint": "f", "retry_capsule_sha256": "r"},
        ),
        "skill": work(
            "skill", "VERIFY_SKILL_CANDIDATE", 20,
            payload={"candidate": candidate},
            identity={"candidate_sha256": "sha256:c2"},
        ),
    })
    driver.authenticate_skill_verification = lambda candidate, binding, repo_root: {
        "pass": True,
        "verified_skill": {
            **candidate,
            "reuse_authorized": True,
            "scope_relation": "EXACT",
        },
    }
    out = driver.drain(
        state_path=path,
        failure_repair_provider=lambda w: {"pass": False, "status": "BLOCKED", "reason": "no safe replay"},
        skill_verification_provider=lambda req: {"receipt": {"path": "r"}, "verification": {"path": "v"}},
        max_actions=2,
    )
    assert len(out["actions"]) == 2, out
    assert out["actions"][0]["attempt_backoff_recorded"] is True, out
    assert out["actions"][1]["progress"] is True, out
    assert out["progress_count"] == 1, out

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "state.json"
    make_state(path, {
        "collect": work("collect", "COLLECT_MATCHING_VERIFIED_EPISODE", 40)
    })
    out = driver.advance_once(state_path=path)
    assert out["pass"] is True and out["progress"] is False, out
    assert out["blockers"][0]["blocker"] == "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE", out

print(json.dumps({
    "status": "PASS",
    "verified": [
        "exact_current_source_compile",
        "evidence_bound_verifier_backoff",
        "same_evidence_no_retry",
        "new_evidence_retry",
        "failed_repair_no_starvation",
        "event_wait_no_false_progress"
    ]
}, sort_keys=True))
