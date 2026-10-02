from __future__ import annotations

from itertools import product

from canonical.runtime import delegation_receipt_history_candidate_v4 as v4


def base_task():
    return {
        "initial_facts": [],
        "required_outputs": ["DONE"],
        "resource_capacities": {"R1": 2, "R2": 1},
        "steps": [
            {
                "id": "S1", "requires": [], "produces": ["MID"], "capability": "C",
                "cost": 1, "writes": ["R1"], "evidence_outputs": ["E1"],
            },
            {
                "id": "S2", "requires": ["MID"], "produces": ["DONE"], "capability": "D",
                "cost": 1, "writes": ["R2"], "evidence_outputs": ["E2"],
            },
        ],
        "workers": [
            {"id": "W1", "capabilities": ["C", "D"]},
            {"id": "W2", "capabilities": ["C", "D"]},
            {"id": "W3", "capabilities": ["D"]},
        ],
    }


EVENTS = (
    ("STEP_UNAVAILABLE", "S1", None, None),
    ("STEP_UNAVAILABLE", "S2", None, None),
    ("WORKER_UNAVAILABLE", "W1", None, None),
    ("WORKER_UNAVAILABLE", "W2", None, None),
    ("WORKER_CAPABILITY_REMOVED", "W1", "C", None),
    ("WORKER_CAPABILITY_REMOVED", "W2", "D", None),
    ("RESOURCE_CAPACITY_CHANGED", "R1", None, 1),
    ("RESOURCE_CAPACITY_CHANGED", "R1", None, 3),
)


def row(i, ev):
    kind, entity, cap, capacity = ev
    out = {
        "receipt_id": f"R{i}",
        "kind": kind,
        "entity_id": entity,
        "completed_task_ids": [],
    }
    if cap is not None:
        out["capability"] = cap
    if capacity is not None:
        out["capacity"] = capacity
    return out


def abstract(task, history):
    disabled = set()
    unavailable = set()
    removed = {}
    resources = dict(task["resource_capacities"])
    for r in history:
        if r["kind"] == "STEP_UNAVAILABLE":
            disabled.add(r["entity_id"])
        elif r["kind"] == "WORKER_UNAVAILABLE":
            unavailable.add(r["entity_id"])
        elif r["kind"] == "WORKER_CAPABILITY_REMOVED":
            removed.setdefault(r["entity_id"], set()).add(r["capability"])
        elif r["kind"] == "RESOURCE_CAPACITY_CHANGED":
            resources[r["entity_id"]] = r["capacity"]

    steps = {
        x["id"]: (x.get("available", True) is True and x["id"] not in disabled)
        for x in task["steps"]
    }
    workers = {
        x["id"]: tuple(c for c in x["capabilities"] if c not in removed.get(x["id"], set()))
        for x in task["workers"]
        if x["id"] not in unavailable
    }
    return steps, workers, resources


def concrete(task, history):
    materialized, completed = v4._apply_history(task, history)
    assert completed == []
    steps = {x["id"]: x["available"] for x in materialized["steps"]}
    workers = {x["id"]: tuple(x["capabilities"]) for x in materialized["workers"]}
    return steps, workers, materialized["resource_capacities"]


def main():
    task = base_task()
    checked = 0
    for n in range(5):
        for choice in product(EVENTS, repeat=n):
            history = [row(i, ev) for i, ev in enumerate(choice)]
            want = abstract(task, history)
            got = concrete(task, history)
            assert got == want, (history, got, want)
            checked += 1

    # Directly pin the old resurrection witness against V4.
    p0 = v4.solve_initial({"task": {
        "initial_facts": [], "required_outputs": ["DONE"], "resource_capacities": {},
        "steps": [{"id": "S", "requires": [], "produces": ["DONE"], "capability": "C",
                   "cost": 1, "writes": [], "evidence_outputs": ["E"]}],
        "workers": [
            {"id": "W1", "capabilities": ["C"]},
            {"id": "W2", "capabilities": ["C"]},
            {"id": "W3", "capabilities": ["C"]},
        ],
    }})
    t = {
        "initial_facts": [], "required_outputs": ["DONE"], "resource_capacities": {},
        "steps": [{"id": "S", "requires": [], "produces": ["DONE"], "capability": "C",
                   "cost": 1, "writes": [], "evidence_outputs": ["E"]}],
        "workers": [
            {"id": "W1", "capabilities": ["C"]},
            {"id": "W2", "capabilities": ["C"]},
            {"id": "W3", "capabilities": ["C"]},
        ],
    }
    r1 = {"receipt_id": "X1", "kind": "WORKER_UNAVAILABLE", "entity_id": "W1", "completed_task_ids": []}
    r2 = {"receipt_id": "X2", "kind": "WORKER_UNAVAILABLE", "entity_id": "W2", "completed_task_ids": []}
    p1 = v4.solve_after_receipt({"task": t, "receipt": r1}, p0)
    p2 = v4.solve_after_receipt({"task": t, "receipt": r2}, p1)
    assert p0["assignment"]["S"] == "W1"
    assert p1["assignment"]["S"] == "W2"
    assert p2["assignment"]["S"] == "W3"
    assert p2["receipt_history_ids"] == ["X1", "X2"]

    print(f"INDEPENDENT_HISTORY_MODEL_PASS histories={checked}")


if __name__ == "__main__":
    main()
