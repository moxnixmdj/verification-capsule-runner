from __future__ import annotations

import json
from canonical.runtime.common_frozen_tool_authority_v1 import (
    AuthorityError,
    CommonFrozenToolAuthority,
    prove_common_authority_instance,
)
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def run_episode(entries, mask):
    a = CommonFrozenToolAuthority(entries, epoch=mask)
    public = a.initial_public_state(
        "BRAIN",
        required_capabilities=["CAP"],
        initial_visible_ids=[entries[0]["tool_id"]],
        episode_epoch=mask,
    )
    for _ in range(100):
        action = v4.next_action(public)
        kind = action["action"]
        if kind == "DISCOVER":
            public = a.apply_discover(public, action, "BRAIN", episode_epoch=mask)
        elif kind == "PROBE":
            public = a.apply_probe(public, action, "BRAIN", episode_epoch=mask)
        elif kind == "SELECT":
            return action["tool_id"], public
        elif kind == "ESCALATE":
            return None, public
        else:
            raise AssertionError(action)
    raise AssertionError("episode action budget exceeded")


def main():
    names = ["opaque::Q9", "opaque::Q7", "opaque::Q5", "opaque::Q3", "opaque::Q1"]
    costs = [9.0, 7.0, 5.0, 3.0, 1.0]

    for mask in range(1 << len(names)):
        entries = []
        for i, (name, cost) in enumerate(zip(names, costs)):
            entries.append({
                "tool_id": name,
                "cost": cost,
                "available": True,
                "authorized": True,
                "region": "X",
                "capabilities": ["CAP"] if mask & (1 << i) else [],
            })
        selected, public = run_episode(entries, mask)
        sufficient = [e for e in entries if "CAP" in e["capabilities"]]
        expected = min(sufficient, key=lambda x: (x["cost"], x["tool_id"]))["tool_id"] if sufficient else None
        assert selected == expected, (mask, selected, expected)
        assert len(public["discovery_receipts"]) == 1, (mask, public["discovery_receipts"])
        discovered = {
            row["tool_id"]
            for row in public["discovery_receipts"][0]["tools"]
        }
        assert discovered == set(names), (mask, discovered)

    authority = CommonFrozenToolAuthority([
        {
            "tool_id": "nonsemantic::α",
            "cost": 1.0,
            "available": True,
            "authorized": True,
            "capabilities": ["X"],
        }
    ], epoch=77)
    b = authority.discover("BRAIN", episode_epoch=77)
    o = authority.discover("OPUS55", episode_epoch=77)
    assert b == o
    assert b["authority_digest_sha256"] == authority.authority_digest_sha256()
    assert "capabilities" not in b["tools"][0]

    for route in ("BRAIN", "OPUS55"):
        try:
            authority.invoke(route, "unregistered", episode_epoch=77)
        except AuthorityError as exc:
            assert "UNREGISTERED_TOOL_ID" in str(exc)
        else:
            raise AssertionError("unregistered invocation was not blocked: " + route)

    old = authority.epoch
    authority.replace_authority([
        {
            "tool_id": "nonsemantic::β",
            "cost": 2.0,
            "available": True,
            "authorized": True,
            "capabilities": ["X"],
        }
    ])
    for route in ("BRAIN", "OPUS55"):
        try:
            authority.discover(route, episode_epoch=old)
        except AuthorityError as exc:
            assert "EPOCH_CHANGED_RESTART_EPISODE" in str(exc)
        else:
            raise AssertionError("stale episode did not fail closed: " + route)

    projection = prove_common_authority_instance(authority)
    assert projection["common_frozen_authority_not_brain_only"] is True
    assert projection["exact_complete_identity_enumeration"] is True
    assert projection["hidden_capability_truth_not_disclosed_by_discovery"] is True

    print(json.dumps({
        "status": "PASS",
        "capability_masks_exhausted": 32,
        "common_route_digest_equal": True,
        "unregistered_invocation_fail_closed": True,
        "epoch_change_fail_closed": True,
        "zero_credit": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
