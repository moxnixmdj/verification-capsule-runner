from __future__ import annotations

import copy
import hashlib
import json
import threading
from itertools import chain, combinations
from pathlib import Path

from canonical.runtime.instruction_authority_invariant_v1 import (
    AuthorityCommitError,
    InstructionAuthorityCommitGate,
    evaluate_instruction_action,
)

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/instruction_authority_invariant_v1.py": "78f4926de6da3f724c1ccd33b4ae83506cca5a0f",
    "canonical/tests/test_instruction_authority_invariant_v1.py": "0e4f24038da5ab3ee3adb25b92c22fb4614251df",
    "canonical/runtime/requirement_graph_kernel.py": "18001b4b7ace6fe77497c7fb92dd8d9dd2d0f607"
}
BRAIN_PR = 2198
BRAIN_HEAD = "d320cc2845a79d11a3b1df7d502b0a350febddc3"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(cond, msg):
    if not cond:
        raise AssertionError(msg)


def expect_error(code, fn):
    try:
        fn()
    except AuthorityCommitError as exc:
        require(code in str(exc), f"wrong failure for {code}: {exc}")
        return
    raise AssertionError("expected failure: " + code)


def req(rid):
    return {
        "id": rid,
        "critical": True,
        "dependencies": [],
        "children": [],
        "open_questions": [],
        "clauses": [{
            "id": rid + ":must",
            "keyword": "MUST",
            "covered_by_scenarios": [rid + ":scenario"],
        }],
        "scenarios": [{
            "id": rid + ":scenario",
            "given": ["normalized requirement"],
            "when": ["action proposed"],
            "then": ["authority invariant checked"],
        }],
    }


def base_state():
    return {
        "current_epoch": 3,
        "active_requirement_ids": ["R1", "R2"],
        "superseded_requirement_ids": [],
        "authorized_scopes": ["read", "write"],
        "forbidden_scopes": ["delete"],
        "unresolved_authority_questions": [],
    }


def proposal(scopes=None):
    return {
        "action_id": "A1",
        "epoch": 3,
        "requirement_ids": ["R1", "R2"],
        "required_scopes": list(scopes or ["read"]),
    }


def powerset(xs):
    xs=list(xs)
    return chain.from_iterable(combinations(xs,r) for r in range(len(xs)+1))


def main():
    for rel, expected in EXPECTED.items():
        actual=git_blob_sha((ROOT / rel).read_bytes())
        require(actual == expected, f"exact blob mismatch {rel}: {actual} != {expected}")

    requirements=[req("R1"),req("R2")]

    # Independent finite-state check of the point-in-time theorem.
    universe=["read","write"]
    checked=0
    for authorized in powerset(universe):
        for forbidden in powerset(universe):
            for required in powerset(universe):
                for epoch in (2,3,4):
                    for unresolved in ([],["q"]):
                        st={
                            "current_epoch":3,
                            "active_requirement_ids":["R1","R2"],
                            "superseded_requirement_ids":[],
                            "authorized_scopes":list(authorized),
                            "forbidden_scopes":list(forbidden),
                            "unresolved_authority_questions":unresolved,
                        }
                        p=proposal(required)
                        p["epoch"]=epoch
                        out=evaluate_instruction_action(requirements,st,p)
                        checked += 1
                        require(out.get("execution_authority") is False,
                                "snapshot evaluator leaked durable execution authority")
                        if out.get("point_in_time_authority"):
                            require(epoch == 3, "stale/future epoch admitted")
                            require(not unresolved, "unresolved ambiguity admitted")
                            require(set(required) <= set(authorized), "unauthorized scope admitted")
                            require(not (set(required) & set(forbidden)), "forbidden scope admitted")
                            require(not (set(authorized) & set(forbidden)), "contradictory authority admitted")

    # Exact stale-grant counterexample must now fail.
    gate=InstructionAuthorityCommitGate(requirements,base_state())
    g=gate.issue_grant(proposal(),grant_id="stale")
    require(g["pass"] is True, "grant issue failed")
    gate.advance_requirements(
        [req("R2"),req("R3")],
        active_requirement_ids=["R2","R3"],
        authorized_scopes=["read"],
        forbidden_scopes=["write","delete"],
    )
    effect_calls=[]
    try:
        gate.commit(g["grant"],proposal(),lambda: effect_calls.append("BAD"))
    except AuthorityCommitError:
        pass
    else:
        raise AssertionError("stale grant committed after requirement change")
    require(effect_calls == [], "stale effect executed")

    # Replay and action/state mutation must fail closed.
    gate=InstructionAuthorityCommitGate(requirements,base_state())
    g=gate.issue_grant(proposal(),grant_id="once")
    calls=[]
    gate.commit(g["grant"],proposal(),lambda: calls.append("OK"))
    require(calls == ["OK"], "baseline effect count wrong")
    expect_error("GRANT_REPLAY_FORBIDDEN",
                 lambda: gate.commit(g["grant"],proposal(),lambda: calls.append("REPLAY")))
    require(calls == ["OK"], "replay effect executed")

    gate=InstructionAuthorityCommitGate(requirements,base_state())
    g=gate.issue_grant(proposal(),grant_id="action")
    p2=proposal()
    p2["action_id"]="A2"
    expect_error("GRANT_ACTION_DIGEST_MISMATCH",
                 lambda: gate.commit(g["grant"],p2,lambda: None))

    gate=InstructionAuthorityCommitGate(requirements,base_state())
    g=gate.issue_grant(proposal(),grant_id="state")
    forged=copy.deepcopy(g["grant"])
    forged["normalized_authority_state_digest"]="f"*64
    expect_error("GRANT_STATE_DIGEST_MISMATCH",
                 lambda: gate.commit(forged,proposal(),lambda: None))

    # Failure consumes authority, eliminating replay after a partial/unknown effect.
    gate=InstructionAuthorityCommitGate(requirements,base_state())
    g=gate.issue_grant(proposal(),grant_id="partial")
    def boom():
        raise RuntimeError("effect failed")
    try:
        gate.commit(g["grant"],proposal(),boom)
    except RuntimeError:
        pass
    else:
        raise AssertionError("failing effect unexpectedly succeeded")
    expect_error("GRANT_REPLAY_FORBIDDEN",
                 lambda: gate.commit(g["grant"],proposal(),lambda: None))

    # Independent interleaving test: epoch update cannot complete while effect owns commit lock.
    gate=InstructionAuthorityCommitGate(requirements,base_state())
    g=gate.issue_grant(proposal(),grant_id="linear")
    entered=threading.Event()
    release=threading.Event()
    update_started=threading.Event()
    update_done=threading.Event()
    errors=[]

    def effect():
        entered.set()
        if not release.wait(3):
            raise RuntimeError("release timeout")
        return "done"

    def do_commit():
        try:
            gate.commit(g["grant"],proposal(),effect)
        except BaseException as exc:
            errors.append(repr(exc))

    def do_update():
        update_started.set()
        try:
            gate.advance_requirements(
                [req("R2"),req("R3")],
                active_requirement_ids=["R2","R3"],
                authorized_scopes=["read"],
                forbidden_scopes=["write","delete"],
            )
            update_done.set()
        except BaseException as exc:
            errors.append(repr(exc))

    t1=threading.Thread(target=do_commit)
    t2=threading.Thread(target=do_update)
    t1.start()
    require(entered.wait(2), "effect never entered")
    t2.start()
    require(update_started.wait(2), "update never started")
    require(not update_done.wait(0.1), "authority update interleaved with effect")
    release.set()
    t1.join(3); t2.join(3)
    require(not t1.is_alive() and not t2.is_alive(), "thread did not terminate")
    require(update_done.is_set(), "authority update did not complete after effect")
    require(errors == [], "thread errors: " + repr(errors))
    require(gate.snapshot()["current_epoch"] == 4, "epoch did not advance")

    print(json.dumps({
        "status":"PASS",
        "brain_pr":BRAIN_PR,
        "brain_head":BRAIN_HEAD,
        "exact_blobs":EXPECTED,
        "point_in_time_states_checked":checked,
        "verified":[
            "exact_blob_identity",
            "snapshot_never_returns_durable_execution_authority",
            "finite_point_in_time_authority_soundness",
            "stale_grant_rejection_after_epoch_change",
            "one_use_replay_rejection",
            "action_digest_binding",
            "state_digest_binding",
            "failed_effect_consumes_grant",
            "requirement_change_serialized_against_effect",
        ],
        "not_verified":[
            "semantic_extraction_completeness",
            "universal_execution_route_coverage",
            "matched_opus55_noninferiority",
            "terminal_predicate_closure",
        ],
        "fresh_reality_units_consumed":0,
        "acceptance_credit_delta":0,
        "incremental_spend_usd":0,
    },indent=2))


if __name__ == "__main__":
    main()
