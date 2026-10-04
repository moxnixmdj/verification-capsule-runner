#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
import tempfile
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
HF_REVISION = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
HF_PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
TARGET_RELEASE = "2026-06-25"
OLD_IF_BOUNDARY = "2025-11-25"

SOURCES = {
    "common": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/common.py",
        "95373cc6a82bc935013e2c23d2a183022f802f5c",
    ),
    "judge": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/gen_ground_truth_judgment.py",
        "b36561da5b54380c724c507462d0ee65feefeac8",
    ),
    "legacy_registry": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval/instructions_registry.py",
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    ),
    "legacy_eval": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval/evaluation_main.py",
        "4a341984936c4d609644a3b77f8c030ac5aa7269",
    ),
}

PARQUET_URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    f"{HF_REVISION}/data/test-00000-of-00001.parquet?download=true"
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "project-brain-independent-verifier"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def norm_date(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 else s


def extract_release_set(common_src: str) -> set[str]:
    m = re.search(r"LIVE_BENCH_RELEASES\s*=\s*(\{[^\n]+\})", common_src)
    assert m, "LIVE_BENCH_RELEASES_NOT_FOUND"
    value = ast.literal_eval(m.group(1))
    assert isinstance(value, set)
    return {str(x) for x in value}


def _const_env(tree: ast.AST) -> dict[str, str]:
    env: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            env[target.id] = node.value.value
    return env


def _eval_str(node: ast.AST, env: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _eval_str(node.left, env) + _eval_str(node.right, env)
    raise ValueError(ast.dump(node))


def legacy_instruction_ids(registry_src: str) -> list[str]:
    tree = ast.parse(registry_src)
    env = _const_env(tree)
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "INSTRUCTION_DICT":
            assert isinstance(node.value, ast.Dict)
            return [_eval_str(k, env) for k in node.value.keys]
    raise AssertionError("INSTRUCTION_DICT_NOT_FOUND")


def main() -> int:
    fetched: dict[str, bytes] = {}
    blob_receipt = {}
    for name, (url, expected_blob) in SOURCES.items():
        raw = fetch(url)
        observed = git_blob_sha(raw)
        assert observed == expected_blob, (name, observed, expected_blob)
        fetched[name] = raw
        blob_receipt[name] = observed

    common_src = fetched["common"].decode("utf-8")
    judge_src = fetched["judge"].decode("utf-8")
    registry_src = fetched["legacy_registry"].decode("utf-8")
    legacy_eval_src = fetched["legacy_eval"].decode("utf-8")

    # Reproduce the exact public loader/filter and official dispatch contract.
    releases = extract_release_set(common_src)
    assert TARGET_RELEASE in releases
    eligible_releases = {r for r in releases if r <= TARGET_RELEASE}
    assert "q['livebench_removal_date'] == \"\" or q['livebench_removal_date'] > livebench_release" in common_src

    assert (
        "m.question.get('category') == 'instruction_following' and "
        "m.question.get(\"livebench_release_date\", \"\") < \"2025-11-25\""
    ) in judge_src
    assert "old_instruction_following_matches" in judge_src
    assert "instruction_following_process_results" in judge_src
    assert "ifbench_process_results" in judge_src

    ids = legacy_instruction_ids(registry_src)
    assert len(ids) == 25, len(ids)
    assert len(set(ids)) == 25
    assert "keywords:existence" in ids
    assert "combination:repeat_prompt" in ids
    assert "startend:quotation" in ids
    assert "instruction_following_process_results" in legacy_eval_src

    parquet = fetch(PARQUET_URL)
    observed_parquet = hashlib.sha256(parquet).hexdigest()
    assert observed_parquet == HF_PARQUET_SHA256, observed_parquet

    # Privacy/contamination discipline: decode only aggregate routing metadata.
    # Prompt/turn/kwargs/question_id columns are never projected into memory.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "if.parquet"
        p.write_bytes(parquet)
        table = pq.read_table(
            p,
            columns=[
                "task",
                "livebench_release_date",
                "livebench_removal_date",
            ],
        )

    tasks = table.column("task").to_pylist()
    release_dates = [norm_date(x) for x in table.column("livebench_release_date").to_pylist()]
    removal_dates = [norm_date(x) for x in table.column("livebench_removal_date").to_pylist()]

    assert len(tasks) == len(release_dates) == len(removal_dates) == 400

    active = []
    for task, released, removed in zip(tasks, release_dates, removal_dates):
        if released not in eligible_releases:
            continue
        if removed == "" or removed > TARGET_RELEASE:
            active.append((str(task), released))

    active_task_counts = Counter(task for task, _ in active)
    active_release_dates = [released for _, released in active]

    assert len(active) == 200, len(active)
    assert active_task_counts == Counter({
        "paraphrase": 50,
        "simplify": 50,
        "story_generation": 50,
        "summarize": 50,
    }), active_task_counts
    assert active_release_dates
    assert max(active_release_dates) < OLD_IF_BOUNDARY
    assert min(active_release_dates) >= min(eligible_releases)

    # Therefore every active row is routed into old_instruction_following_matches,
    # not normal_matches / ifbench_process_results.
    old_route_count = sum(d < OLD_IF_BOUNDARY for d in active_release_dates)
    modern_route_count = len(active_release_dates) - old_route_count
    assert old_route_count == 200
    assert modern_route_count == 0

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_IF_2026_TERMINAL_SCORER_SCOPE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "pinned": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "hf_revision": HF_REVISION,
            "hf_parquet_sha256": observed_parquet,
            "source_git_blobs": blob_receipt,
            "target_release": TARGET_RELEASE,
            "old_if_boundary": OLD_IF_BOUNDARY,
        },
        "metadata_only_population_recompute": {
            "decoded_columns": [
                "task",
                "livebench_release_date",
                "livebench_removal_date",
            ],
            "prompt_columns_decoded": False,
            "question_id_decoded": False,
            "kwargs_decoded": False,
            "dataset_rows": len(tasks),
            "active_rows": len(active),
            "active_task_counts": dict(sorted(active_task_counts.items())),
            "active_release_date_min": min(active_release_dates),
            "active_release_date_max": max(active_release_dates),
        },
        "scorer_dispatch": {
            "legacy_active_rows": old_route_count,
            "modern_ifbench_active_rows": modern_route_count,
            "legacy_registry_instruction_count": len(ids),
            "conclusion": "ALL_200_ACTIVE_ROWS_ROUTE_TO_LEGACY_INSTRUCTION_FOLLOWING_EVALUATOR",
        },
        "truth_repair": {
            "modern_58_checkers_on_current_terminal_critical_path": False,
            "load_bearing_instruction_registry_count": 25,
            "prior_83_checker_working_surface_overbroad_for_current_terminal_predicate": True,
            "prior_claim_active_2026_instruction_following_route_uses_ifbench_process_results": False,
        },
        "hard_nonclaims": [
            "NO_PROMPT_TEXT_DECODED_OR_EMITTED",
            "NO_QUESTION_IDS_DECODED_OR_EMITTED",
            "NO_TERMINAL_RESPONSE_OR_RESULT_CONTENT_READ",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_CLAIM_LEGACY_25_ARE_ALREADY_SOLVED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_prompt_cases_exposed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    Path("livebench_terminal_scorer_scope_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
