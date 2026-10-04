#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path("/tmp/LiveBench")
PINNED_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
RELEASE = "2026-06-25"
CUTOFF = "2025-11-25"
EXPECTED = {
    "livebench/gen_ground_truth_judgment.py": "b36561da5b54380c724c507462d0ee65feefeac8",
    "livebench/process_results/instruction_following/utils.py": "8ce01747887ec0792c8f024e1972e34ece781676",
    "livebench/if_runner/ifbench/evaluation_lib.py": "2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
    "livebench/if_runner/ifbench/instructions_registry.py": "adfed4832877566e62970257b50c6fa32c302fb2",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def source(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("FUNCTION_NOT_FOUND:" + name)


def compact(node: ast.AST) -> str:
    return ast.unparse(node).replace(" ", "").replace("\n", "")


head = git("rev-parse", "HEAD")
assert head == PINNED_COMMIT, (head, PINNED_COMMIT)
observed = {rel: git("rev-parse", f"HEAD:{rel}") for rel in EXPECTED}
assert observed == EXPECTED, {"observed": observed, "expected": EXPECTED}

router_src = source("livebench/gen_ground_truth_judgment.py")
router = ast.parse(router_src)
gen = function(router, "gen_judgments")
play = function(router, "play_a_match_gt")

# Bind the release split exactly from syntax rather than from comments.
old_assignment = None
normal_assignment = None
for node in ast.walk(gen):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id == "old_instruction_following_matches":
            old_assignment = node.value
        elif node.targets[0].id == "normal_matches":
            normal_assignment = node.value
assert old_assignment is not None and normal_assignment is not None
old_text = compact(old_assignment)
normal_text = compact(normal_assignment)
assert "category" in old_text and "instruction_following" in old_text
assert "livebench_release_date" in old_text
assert "<'2025-11-25'" in old_text or '<"2025-11-25"' in old_text
assert "old_instruction_following_matches" in normal_text
assert RELEASE >= CUTOFF

# The old evaluator must occur only in the legacy batch path inside gen_judgments.
legacy_calls = [
    n for n in ast.walk(gen)
    if isinstance(n, ast.Call)
    and isinstance(n.func, ast.Name)
    and n.func.id == "instruction_following_process_results"
]
assert len(legacy_calls) == 1

# The per-question normal instruction-following route must call IFBench.
play_text = compact(play)
assert "question.get('category')=='instruction_following'" in play_text or 'question.get("category")=="instruction_following"' in play_text
assert "ifbench_process_results(question,llm_answer,debug)" in play_text

utils_src = source("livebench/process_results/instruction_following/utils.py")
utils = ast.parse(utils_src)
ifbench = function(utils, "ifbench_process_results")
score_results = function(utils, "score_results")
ifbench_text = compact(ifbench)
score_text = compact(score_results)
assert "evaluation_lib.test_instruction_following_strict(inp,response)" in ifbench_text
assert "score_results(result.follow_all_instructions,result.follow_instruction_list)" in ifbench_text
assert "score_1=1iffollow_all_instructionselse0" in score_text
assert "score_2=sum(score_2)/len(score_2)" in score_text
assert "avg_score=(score_1+score_2)/2" in score_text

registry_src = source("livebench/if_runner/ifbench/instructions_registry.py")
registry = ast.parse(registry_src)
registry_node = None
for node in registry.body:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "INSTRUCTION_DICT":
        registry_node = node.value
        break
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in node.targets):
        registry_node = node.value
        break
assert isinstance(registry_node, ast.Dict)
keys = [k.value for k in registry_node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
assert len(keys) == 58, len(keys)
assert len(set(keys)) == 58

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_2026_06_25_IFBENCH58_SCORER_ROUTE_INDEPENDENT_VERIFICATION_V1",
    "status": "PASS__PINNED_2026_06_25_ROUTES_TO_IFBENCH58_STRICT_NOT_LEGACY25__ZERO_TERMINAL_CONTENT__ZERO_CREDIT",
    "pinned_commit": PINNED_COMMIT,
    "exact_source_blobs": observed,
    "release": RELEASE,
    "legacy_cutoff": CUTOFF,
    "release_is_not_legacy": RELEASE >= CUTOFF,
    "legacy_instruction_following_process_call_count_in_gen_judgments": len(legacy_calls),
    "normal_instruction_following_calls_ifbench_process_results": True,
    "ifbench_calls_strict_evaluator": True,
    "score_formula": "(ALL_INSTRUCTIONS_FOLLOWED_INDICATOR + FRACTION_OF_INSTRUCTIONS_FOLLOWED) / 2",
    "ifbench_registry_count": len(keys),
    "legacy25_load_bearing_for_2026_06_25": False,
    "ifbench58_load_bearing_for_2026_06_25": True,
    "terminal_prompt_text_read": False,
    "terminal_response_text_read": False,
    "terminal_kwargs_read": False,
    "terminal_case_content_read": False,
    "terminal_cases_consumed": 0,
    "acceptance_credit_delta": 0,
    "family_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
}
path = pathlib.Path("livebench_2026_ifbench58_route_v1_receipt.json")
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True))
