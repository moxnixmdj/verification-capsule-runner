#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject" / "root2_global_cut_instruction_v1"
EXPECTED = {
    "root2_global_information_cut_v1.py": "2c2d8ff476f076fc38caf81d3b53f7a2054b83ef",
    "instruction_constraint_compiler_v1.py": "8bdf2c4221f15b5e5cef4b0862e628d896e68d8f",
    "test_root2_global_information_cut_v1.py": "69721a937d4de682bee407ab62ab3a79f5a72648",
    "test_instruction_constraint_compiler_v1.py": "199bbd8071f338f6390932ea42de184f05199c39",
}


def git_blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def load(name: str):
    path = SUB / (name + ".py")
    spec = importlib.util.spec_from_file_location("verify_" + name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC:" + name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def verify_exact_bytes() -> None:
    for name, expected in EXPECTED.items():
        observed = git_blob_sha(SUB / name)
        if observed != expected:
            raise AssertionError(f"BLOB_DRIFT:{name}:{observed}:{expected}")


def brute_force_cut(cut) -> dict:
    rng = random.Random(20261004)
    checked = 0
    for _ in range(120):
        npred = rng.randint(1, 4)
        naction = rng.randint(1, 7)
        preds = [f"P{i}" for i in range(npred)]
        actions = []
        for i in range(naction):
            deps = tuple(
                f"A{j}" for j in range(i)
                if rng.random() < 0.18
            )
            closes = frozenset(
                p for p in preds if rng.random() < 0.38
            )
            actions.append(cut.Action(
                f"A{i}",
                closes,
                float(rng.randint(0, 8)),
                rng.randint(0, 1),
                1,
                deps,
            ))
        # Ensure at least one reachable predicate so optimization is exercised.
        if not any(a.closes for a in actions):
            actions[0] = cut.Action(
                actions[0].action_id,
                frozenset({preds[0]}),
                actions[0].wall_clock_s,
                actions[0].reality_units,
                actions[0].action_count,
                actions[0].dependencies,
            )
        by_id = {a.action_id: a for a in actions}
        reachable = set()
        for aid in by_id:
            reachable.update(cut._effective_closes(aid, by_id))

        best = None
        best_roots = None
        ids = list(by_id)
        for mask in range(1 << len(ids)):
            roots = frozenset(ids[i] for i in range(len(ids)) if mask & (1 << i))
            covered = set()
            for aid in roots:
                covered.update(cut._effective_closes(aid, by_id))
            if not reachable.issubset(covered):
                continue
            cost = cut._cost(roots, by_id)
            if best is None or cost < best:
                best, best_roots = cost, roots

        out = cut.solve(preds, actions)
        got_roots = frozenset(out["selected_root_actions"])
        got_cost = cut._cost(got_roots, by_id)
        if best is None:
            raise AssertionError("BRUTE_FORCE_NO_SOLUTION")
        if got_cost != best:
            raise AssertionError(json.dumps({
                "error": "CUT_NOT_EXACT",
                "predicates": preds,
                "actions": [a.__dict__ for a in actions],
                "expected_cost": best,
                "expected_roots": sorted(best_roots),
                "got_cost": got_cost,
                "got_roots": sorted(got_roots),
            }, default=list, sort_keys=True))
        checked += 1

    # Explicit dependency-reuse case that breaks naïve per-mask DP.
    actions = [
        cut.Action("D", frozenset(), 1, 0, 1, ()),
        cut.Action("A", frozenset({"P0"}), 1, 0, 1, ("D",)),
        cut.Action("B", frozenset({"P1"}), 1, 0, 1, ("D",)),
        cut.Action("C", frozenset({"P0"}), 4, 0, 1, ()),
        cut.Action("E", frozenset({"P1"}), 4, 0, 1, ()),
    ]
    out = cut.solve(["P0", "P1"], actions)
    if out["objective"]["critical_path_wall_clock_s"] != 2.0:
        raise AssertionError("DEPENDENCY_CRITICAL_PATH_WRONG")
    if set(out["selected_root_actions"]) != {"A", "B"}:
        raise AssertionError("SHARED_DEPENDENCY_ROUTE_NOT_SELECTED")
    if set(out["selected_with_dependencies"]) != {"A", "B", "D"}:
        raise AssertionError("SHARED_DEPENDENCY_NOT_ACCOUNTED")
    return {"random_exact_instances": checked, "dependency_reuse_case": "PASS"}


def verify_instruction_compiler(ic) -> dict:
    cases = 0

    out = ic.synthesize_formal_only('Reply with exactly "ALPHA".')
    assert out["status"] == "PASS" and out["response"] == "ALPHA"
    cases += 1

    out = ic.synthesize_formal_only('Reply with exactly "ALPHA". Use lowercase only.')
    assert out["status"] == "BLOCKED"
    cases += 1

    c = ic.compile_constraints('Do not include the word "omega".')
    assert c.required_literals == () and c.forbidden_literals == ("omega",)
    cases += 1

    out = ic.synthesize_formal_only("Use exactly 5 words and include exactly 2 numbers.")
    assert out["status"] == "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED"
    ok, errors = ic.validate_response(out["response"], ic.compile_constraints("Use exactly 5 words and include exactly 2 numbers."))
    assert ok, errors
    cases += 1

    try:
        ic.compile_constraints("Use at least 9 words and at most 3 words.")
    except ic.ConstraintError:
        pass
    else:
        raise AssertionError("WORD_RANGE_CONTRADICTION_NOT_BLOCKED")
    cases += 1

    out = ic.synthesize_formal_only("Explain photosynthesis.")
    assert out["status"] == "BLOCKED" and out["semantic_seed_required"] is True
    cases += 1

    # The compiler must not turn structural satisfaction into a semantic-success claim.
    out = ic.synthesize_formal_only('Include the word "alpha" and use at least 4 words.')
    assert out["semantic_seed_required"] is True
    assert out["status"] != "PASS"
    cases += 1

    return {"synthetic_instruction_cases": cases, "semantic_fail_closed": True}


def main() -> int:
    verify_exact_bytes()
    cut = load("root2_global_information_cut_v1")
    ic = load("instruction_constraint_compiler_v1")
    result = {
        "schema": "PROJECT_BRAIN_ROOT2_GLOBAL_CUT_INSTRUCTION_PUBLIC_RUNNER_VERIFICATION_V1",
        "exact_subject_blobs": EXPECTED,
        "global_cut": brute_force_cut(cut),
        "instruction_compiler": verify_instruction_compiler(ic),
        "network_used": False,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "conclusion": "PASS",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
