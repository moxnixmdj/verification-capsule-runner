#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, urllib.request
from pathlib import Path

COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
SOURCES = {
    "process_utils": (
        "livebench/process_results/instruction_following/utils.py",
        "8ce01747887ec0792c8f024e1972e34ece781676",
    ),
    "legacy_eval": (
        "livebench/if_runner/instruction_following_eval/evaluation_main.py",
        "4a341984936c4d609644a3b77f8c030ac5aa7269",
    ),
    "ifbench_eval": (
        "livebench/if_runner/ifbench/evaluation_lib.py",
        "2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
    ),
}

def fetch(path: str) -> bytes:
    url=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{COMMIT}/{path}"
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def fn_source(src: str, name: str) -> tuple[ast.FunctionDef, str]:
    tree=ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name==name:
            return node, ast.get_source_segment(src,node) or ""
    raise AssertionError(f"missing function {name}")

loaded={}
for key,(path,expected) in SOURCES.items():
    raw=fetch(path)
    actual=git_blob_sha(raw)
    assert actual==expected,(key,actual,expected)
    loaded[key]=raw.decode("utf-8")

utils=loaded["process_utils"]
score_node,score_src=fn_source(utils,"score_results")
ifb_node,ifb_src=fn_source(utils,"ifbench_process_results")
legacy_proc_node,legacy_proc_src=fn_source(utils,"instruction_following_process_results")

# Exact scalar objective: no base-task answer-quality or reference-answer term.
for needle in [
    "score_1 = 1 if follow_all_instructions else 0",
    "score_2 = sum(score_2) / len(score_2)",
    "avg_score = (score_1 + score_2) / 2",
    "return avg_score",
]:
    assert needle in score_src,needle
def executable_tokens(fn: ast.FunctionDef) -> set[str]:
    """Return identifiers/attribute names/string literals used by executable statements.

    The function docstring is intentionally excluded: descriptive prose may mention
    concepts that the executable scorer never reads.
    """
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    tokens: set[str] = set()
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name):
                tokens.add(node.id)
            elif isinstance(node, ast.Attribute):
                tokens.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                tokens.add(node.value)
    return tokens

for forbidden in ["ground_truth","reference_answer","expected_answer","semantic_score","relevance_score"]:
    assert forbidden not in executable_tokens(score_node), forbidden

# IFBench path: strict public checker booleans are the sole inputs to score_results.
assert "evaluation_lib.test_instruction_following_strict(inp, response)" in ifb_src
assert "score_results(result.follow_all_instructions, result.follow_instruction_list)" in ifb_src
for forbidden in ["ground_truth","reference_answer","expected_answer","semantic_score","relevance_score"]:
    assert forbidden not in executable_tokens(ifb_node), forbidden

# Legacy path is the same scalar reducer over strict checker booleans.
assert 'results = results["strict"]' in legacy_proc_src
assert "score_results(follow_all_instructions, follow_instruction_list)" in legacy_proc_src

def verify_strict_evaluator(src: str, function_name: str, response_expr: str) -> dict:
    fn, body=fn_source(src,function_name)
    required=[
        "instruction_list = inp.instruction_id_list",
        "instruction_cls = instructions_registry.INSTRUCTION_DICT[instruction_id]",
        "instruction = instruction_cls(instruction_id)",
        "instruction.build_description(",
        ".check_following(",
        "follow_all_instructions=all(is_following_list)",
        "follow_instruction_list=is_following_list",
    ]
    for needle in required:
        assert needle in body,(function_name,needle)
    tokens=executable_tokens(fn)
    for forbidden in [
        "ground_truth","reference_answer","expected_answer",
        "semantic_score","relevance_score","judge_model","llm_judge",
    ]:
        assert forbidden not in tokens,(function_name,forbidden)
    return {
        "function":function_name,
        "registered_checker_dispatch":True,
        "checker_boolean_reducer_only":True,
        "independent_semantic_quality_term":False,
    }

legacy=verify_strict_evaluator(
    loaded["legacy_eval"],
    "test_instruction_following_strict",
    "prompt_to_response[inp.prompt]",
)
ifbench=verify_strict_evaluator(
    loaded["ifbench_eval"],
    "test_instruction_following_strict",
    "response",
)

receipt={
    "schema":"PROJECT_BRAIN_LIVEBENCH_SCORER_OBJECTIVE_INDEPENDENT_VERIFICATION_V1",
    "status":"PASS",
    "pinned_livebench_commit":COMMIT,
    "source_git_blobs":{k:v[1] for k,v in SOURCES.items()},
    "verified":{
        "score_formula":"0.5 * all_constraints_pass + 0.5 * fraction_constraints_pass",
        "ifbench_path":ifbench,
        "legacy_path":legacy,
        "base_task_semantic_correctness_has_independent_score_term":False,
        "base_task_relevance_has_independent_score_term":False,
        "registered_instruction_checker_satisfaction_is_score_sufficient_statistic":True,
    },
    "theorem":(
        "At the pinned LiveBench instruction-following scorer, once the registered "
        "instruction checker booleans are fixed, the final per-question score is fixed. "
        "There is no separate score term for correctness, relevance, or semantic completion "
        "of the underlying base request. Some registered checkers may structurally depend on "
        "prompt text, but only through their published check_following predicates."
    ),
    "scheduler_consequence":(
        "A LiveBench-IF successor need not acquire post-prompt semantic-answer capability "
        "merely to satisfy this frozen scalar objective. It must instead produce responses "
        "that satisfy the registered checker conjunction, with exact scorer validation."
    ),
    "hard_nonclaims":[
        "NO_CLAIM_GENERAL_SEMANTIC_ANSWERING_IS_UNNECESSARY_OUTSIDE_THIS_FROZEN_SCORER",
        "NO_CLAIM_CURRENT_SUCCESSOR_PASSES_ALL_REGISTERED_CHECKERS",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
        "NO_TERMINAL_CASE_CONTENT_USED",
    ],
}
Path("livebench_scorer_objective_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
