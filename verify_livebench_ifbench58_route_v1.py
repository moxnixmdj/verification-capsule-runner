#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
TARGET_RELEASE = "2026-06-25"
CUTOFF = "2025-11-25"
PINS = {
    "livebench/gen_ground_truth_judgment.py": "b36561da5b54380c724c507462d0ee65feefeac8",
    "livebench/process_results/instruction_following/utils.py": "8ce01747887ec0792c8f024e1972e34ece781676",
    "livebench/if_runner/ifbench/evaluation_lib.py": "2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
    "livebench/if_runner/ifbench/instructions_registry.py": "adfed4832877566e62970257b50c6fa32c302fb2",
}


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def source(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("FUNCTION_NOT_FOUND:" + name)


def calls_in(node: ast.AST) -> list[str]:
    out = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            f = child.func
            if isinstance(f, ast.Name):
                out.append(f.id)
            elif isinstance(f, ast.Attribute):
                parts = []
                while isinstance(f, ast.Attribute):
                    parts.append(f.attr)
                    f = f.value
                if isinstance(f, ast.Name):
                    parts.append(f.id)
                out.append(".".join(reversed(parts)))
    return out


def assigned_expr(fn: ast.FunctionDef, target_name: str) -> ast.AST:
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == target_name for t in node.targets):
                return node.value
    raise AssertionError("ASSIGNMENT_NOT_FOUND:" + target_name)


def contains_cutoff_predicate(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Compare) or len(child.ops) != 1:
            continue
        if not isinstance(child.ops[0], ast.Lt):
            continue
        if len(child.comparators) != 1:
            continue
        rhs = child.comparators[0]
        if isinstance(rhs, ast.Constant) and rhs.value == CUTOFF:
            text = ast.unparse(child.left)
            if "livebench_release_date" in text:
                return True
    return False


def branch_calls_ifbench(fn: ast.FunctionDef) -> bool:
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        test_text = ast.unparse(node.test)
        if "instruction_following" not in test_text or "category" not in test_text:
            continue
        if "ifbench_process_results" in calls_in(ast.Module(body=node.body, type_ignores=[])):
            return True
    return False


def extract_registry_keys(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in targets):
            continue
        value = node.value
        if not isinstance(value, ast.Dict):
            raise AssertionError("REGISTRY_NOT_LITERAL_DICT")
        keys = []
        for key in value.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                raise AssertionError("REGISTRY_NONLITERAL_KEY")
            keys.append(key.value)
        return keys
    raise AssertionError("REGISTRY_NOT_FOUND")


def verify() -> dict:
    root = pathlib.Path("/tmp/LiveBench")
    for rel, expected in PINS.items():
        got = git_blob(root / rel)
        assert got == expected, (rel, got, expected)

    router_src = source(root / "livebench/gen_ground_truth_judgment.py")
    router = ast.parse(router_src)
    gen = find_function(router, "gen_judgments")
    old_expr = assigned_expr(gen, "old_instruction_following_matches")
    normal_expr = assigned_expr(gen, "normal_matches")
    assert contains_cutoff_predicate(old_expr)
    assert "old_instruction_following_matches" in ast.unparse(normal_expr)
    assert TARGET_RELEASE >= CUTOFF

    play = find_function(router, "play_a_match_gt")
    assert branch_calls_ifbench(play)

    proc_src = source(root / "livebench/process_results/instruction_following/utils.py")
    proc = ast.parse(proc_src)
    ifproc = find_function(proc, "ifbench_process_results")
    ifproc_calls = calls_in(ifproc)
    assert "evaluation_lib.test_instruction_following_strict" in ifproc_calls
    assert "score_results" in ifproc_calls

    score = find_function(proc, "score_results")
    score_text = ast.unparse(score)
    assert "(score_1 + score_2) / 2" in score_text

    eval_src = source(root / "livebench/if_runner/ifbench/evaluation_lib.py")
    ev = ast.parse(eval_src)
    strict = find_function(ev, "test_instruction_following_strict")
    strict_text = ast.unparse(strict)
    assert "instructions_registry.INSTRUCTION_DICT[instruction_id]" in strict_text
    assert "instruction.check_following(response)" in strict_text
    assert "response.strip()" in strict_text

    reg_src = source(root / "livebench/if_runner/ifbench/instructions_registry.py")
    reg = ast.parse(reg_src)
    registry_keys = extract_registry_keys(reg)
    assert len(registry_keys) == 58
    assert len(set(registry_keys)) == 58

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_2026_06_25_IFBENCH58_ROUTE_PUBLIC_RUNNER_VERIFICATION_20261005_V1",
        "status": "PASS__2026_06_25_IF_ROUTES_TO_STRICT_IFBENCH58__LEGACY25_NOT_LOAD_BEARING",
        "pinned_livebench_commit": LIVEBENCH_COMMIT,
        "pinned_blobs": PINS,
        "target_release": TARGET_RELEASE,
        "legacy_cutoff": CUTOFF,
        "target_is_not_legacy": TARGET_RELEASE >= CUTOFF,
        "normal_if_route": "ifbench_process_results",
        "strict_evaluator": "evaluation_lib.test_instruction_following_strict",
        "score_formula": "(all_followed_indicator + fraction_followed) / 2",
        "ifbench_registry_count": len(registry_keys),
        "terminal_rows_read": 0,
        "terminal_prompts_read": 0,
        "terminal_responses_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "consequence": "LEGACY25_UNION25_IS_HISTORICAL_EVIDENCE_ONLY_FOR_THE_2026_06_25_TARGET; CRITICAL_PATH_MUST_USE_IFBENCH58",
    }
    pathlib.Path("livebench_ifbench58_route_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return receipt


if __name__ == "__main__":
    verify()
