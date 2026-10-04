#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = json.loads(
    (ROOT / "LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V2.json").read_text(
        encoding="utf-8"
    )
)
SERVER = "http://127.0.0.1:8080/v1/chat/completions"
POLICY = SPEC["generation_policy"]
PROMPT_RULE = SPEC["prompt_construction"]


def normalize_generated(text: str) -> str:
    text = str(text or "").strip()
    # V2 permits only post-generation removal of optional thinking blocks and
    # an optional FINAL label. No prompt-side mutation is performed here.
    text = re.sub(r"(?is)^\s*<think>.*?</think>\s*", "", text).strip()
    text = re.sub(r"(?is)^\s*FINAL\s*:\s*", "", text).strip()
    return text


def prompt_for(case: dict) -> str:
    instruction = str(case["instruction"])
    source = str(case.get("source") or "")
    if source == "":
        return instruction
    return instruction + "\n\nTEXT:\n" + source


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def sentence_count(text: str) -> int:
    # Frozen verifier surface: punctuation-terminated surface sentences.
    # A trailing sentence without final punctuation counts once.
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    return len(parts)


def contains_any(text: str, alternatives: list[str]) -> bool:
    low = text.casefold()
    return any(str(x).casefold() in low for x in alternatives)


def ordered_groups_all_members(text: str, groups: list[list[str]]) -> bool:
    """Require all members of each event group, with groups occurring in order.

    This is deliberately at least as strict as a first-token-only interpretation:
    every declared member must appear and the latest member of event i must occur
    before the earliest member of event i+1. Positive evidence therefore cannot
    be manufactured by satisfying only one token from a multi-token event.
    """
    low = text.casefold()
    spans = []
    for group in groups:
        positions = []
        for token in group:
            pos = low.find(str(token).casefold())
            if pos < 0:
                return False
            positions.append((pos, pos + len(str(token))))
        spans.append((min(p for p, _ in positions), max(e for _, e in positions)))
    return all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1))


def call(case: dict) -> tuple[str, float, dict]:
    case_id = case["id"]
    seed = int(POLICY["case_seed_schedule"][case_id])
    expected_seed = int(POLICY["fixed_seed_base"]) + list(
        x["id"] for x in SPEC["frozen_nonterminal_suite"]
    ).index(case_id)
    if seed != expected_seed:
        raise RuntimeError(f"SEED_SCHEDULE_MISMATCH:{case_id}:{seed}:{expected_seed}")

    user_message = prompt_for(case)
    body = {
        "model": "local",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": POLICY["temperature"],
        "top_p": POLICY["top_p"],
        "max_tokens": POLICY["max_tokens"],
        "seed": seed,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        SERVER,
        data=raw,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=300) as response:
        payload = json.loads(response.read(500_000).decode("utf-8", "replace"))
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise RuntimeError("EXACTLY_ONE_CHOICE_REQUIRED")
    message = choices[0].get("message") or {}
    generated = normalize_generated(message.get("content", ""))
    if not generated:
        raise RuntimeError("NONEMPTY_GENERATION_REQUIRED")
    return generated, round(time.monotonic() - started, 3), {
        "seed": seed,
        "user_message_sha256_input": user_message,
        "request_messages": body["messages"],
        "chat_template_kwargs": body["chat_template_kwargs"],
    }


def grade(case: dict, output: str) -> dict:
    checks: dict[str, bool] = {"nonempty": bool(output.strip())}

    if "required_groups" in case:
        checks["required_groups"] = all(
            contains_any(output, group) for group in case["required_groups"]
        )

    source = str(case.get("source") or "")
    if case.get("forbidden_exact") is True:
        checks["forbidden_exact"] = output.strip().casefold() != source.strip().casefold()
    if case.get("min_source_change") is True:
        checks["min_source_change"] = output.strip().casefold() != source.strip().casefold()

    if "max_words" in case:
        checks["max_words"] = word_count(output) <= int(case["max_words"])
    if "max_sentences" in case:
        checks["max_sentences"] = sentence_count(output) <= int(case["max_sentences"])
    if "exact_sentences" in case:
        checks["exact_sentences"] = sentence_count(output) == int(case["exact_sentences"])
    if "ordered_groups" in case:
        checks["ordered_groups"] = ordered_groups_all_members(
            output, case["ordered_groups"]
        )

    return {
        "pass": all(checks.values()),
        "checks": checks,
        "word_count": word_count(output),
        "sentence_count": sentence_count(output),
    }


def main() -> int:
    if PROMPT_RULE["system_message"] is not None:
        raise RuntimeError("V2_SYSTEM_MESSAGE_MUST_BE_NULL")
    if PROMPT_RULE["source_separator_literal"] != "\\n\\nTEXT:\\n":
        raise RuntimeError("V2_SEPARATOR_CONTRACT_CHANGED")
    if POLICY["attempts_per_case"] != 1:
        raise RuntimeError("V2_ONE_ATTEMPT_RULE_CHANGED")
    if POLICY["adaptive_retry"] is not False:
        raise RuntimeError("V2_ADAPTIVE_RETRY_MUST_BE_FALSE")

    rows = []
    for case in SPEC["frozen_nonterminal_suite"]:
        output, duration_s, request_meta = call(case)
        scored = grade(case, output)
        row = {
            "id": case["id"],
            "effect": case["effect"],
            "output": output,
            "duration_s": duration_s,
            "seed": request_meta["seed"],
            "request_messages": request_meta["request_messages"],
            "chat_template_kwargs": request_meta["chat_template_kwargs"],
            **scored,
        }
        rows.append(row)
        print(json.dumps({"progress": row}, ensure_ascii=False), file=sys.stderr, flush=True)

    by_effect: dict[str, list[bool]] = {}
    for row in rows:
        by_effect.setdefault(row["effect"], []).append(bool(row["pass"]))
    effect_pass = {
        effect: len(values) == 2 and all(values)
        for effect, values in sorted(by_effect.items())
    }

    suite_pass = len(rows) == 8 and all(row["pass"] for row in rows) and all(
        effect_pass.values()
    )
    receipt = {
        "schema": "PROJECT_BRAIN_QWEN38_4B_SEMANTIC_SEED_V2_PUBLIC_RUNNER_RECEIPT_V1",
        "status": "PASS" if suite_pass else "FAIL",
        "precommit_git_blob_sha": "e7b78710ac25b6bf1161b139db3b65f906786e66",
        "subject": SPEC["execution_subject"],
        "runtime": SPEC["runtime"],
        "generation_policy": POLICY,
        "prompt_construction": PROMPT_RULE,
        "results": rows,
        "effect_pass": effect_pass,
        "passed_cases": sum(int(row["pass"]) for row in rows),
        "required_cases": 8,
        "terminal_cases_consumed": 0,
        "terminal_prompt_exposure": 0,
        "adaptive_retries": 0,
        "incremental_spend_usd": 0,
        "authority": {
            "terminal_execution": False,
            "promotion": False,
            "acceptance_credit": False,
        },
        "hard_nonclaims": SPEC["hard_nonclaims"],
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if suite_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
