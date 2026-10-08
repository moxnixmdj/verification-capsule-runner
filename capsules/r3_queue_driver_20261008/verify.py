from __future__ import annotations

import json
import sys
import tempfile
import types
from pathlib import Path
import importlib.util

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

def load_state(path):
    p = Path(path)
    if not p.exists():
        return {"episodes": {}, "improvement_queue": {}, "stats": {}}
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

learning.load_state = load_state
learning._write_state = write_state
learning._refresh_stats = refresh_stats
learning.next_improvement_action = next_action
learning._post_execution_independent_verification = lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected verifier call"))
learning.integrate_solver_output = lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected integration call"))
learning.get_success_replay_context = lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected replay call"))
runtime.autonomous_verified_self_improvement_v1 = learning
sys.modules[learning.__name__] = learning

auth = types.ModuleType("canonical.runtime.executable_skill_verification_authenticator_v1")
auth.authenticate_and_verify = lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected skill auth call"))
sys.modules[auth.__name__] = auth

spec = importlib.util.spec_from_file_location("capsule_driver", SOURCE)
driver = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(driver)

def make_state(path, queue):
    state = {"episodes": {}, "improvement_queue": queue, "stats": {}}
    refresh_stats(state)
    write_state(state, path)

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "state.json"
    make_state(path, {
        "skill": {
            "work_id": "skill", "kind": "VERIFY_SKILL_CANDIDATE", "priority": 10,
            "identity": {}, "payload": {}, "status": "PENDING", "observations": 1, "reopen_count": 0,
        },
        "repair": {
            "work_id": "repair", "kind": "REPAIR_FAILURE_CLASS", "priority": 30,
            "identity": {}, "payload": {"failure_fingerprint": "f", "retry_capsule_sha256": "r"},
            "status": "PENDING", "observations": 1, "reopen_count": 0,
        },
    })
    calls = []
    def repair(work):
        calls.append(work["work_id"])
        return {"pass": True, "status": "REPAIRED"}
    out = driver.advance_once(state_path=path, failure_repair_provider=repair)
    assert out["pass"] is True and out["progress"] is True, out
    assert out["work_id"] == "repair", out
    assert out["blockers_skipped"][0]["blocker"] == "SKILL_VERIFICATION_PROVIDER_REQUIRED", out
    assert calls == ["repair"], calls

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "state.json"
    make_state(path, {
        "collect": {
            "work_id": "collect", "kind": "COLLECT_MATCHING_VERIFIED_EPISODE", "priority": 40,
            "identity": {}, "payload": {}, "status": "PENDING", "observations": 1, "reopen_count": 0,
        }
    })
    out = driver.advance_once(state_path=path)
    assert out["pass"] is True and out["progress"] is False, out
    assert out["blockers"][0]["blocker"] == "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE", out
    drained = driver.drain(state_path=path, max_actions=4)
    assert drained["progress_count"] == 0, drained
    assert len(drained["actions"]) == 1, drained
    assert drained["status"] == "IMPROVEMENT_QUEUE_STABLE", drained

print(json.dumps({
    "status": "PASS",
    "source_file": SOURCE.name,
    "verified": [
        "python_compile",
        "blocked_priority_skip",
        "actionable_repair_dispatch",
        "event_wait_no_false_progress",
        "drain_termination",
    ],
}, sort_keys=True))
