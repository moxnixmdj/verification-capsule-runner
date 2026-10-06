#!/usr/bin/env python3
"""Independent exact replay of Brain Qwen3.8-4B semantic-seed precommit V2.

Frozen against canonical Brain commit 6b957a56659c2c7630fe0736cff0fe6e1c5eab47.
No terminal LiveBench cases, hidden metadata, or adaptive retries are used.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_QWEN38_4B_ROOT1_SEMANTIC_SEED_PUBLIC_VERIFICATION_V2"
SERVER = "http://127.0.0.1:8080/v1/chat/completions"
BASE_SEED = 424200
BRAIN_PRECOMMIT_COMMIT = "6b957a56659c2c7630fe0736cff0fe6e1c5eab47"
SOURCE_SEPARATOR = "\n\nTEXT:\n"

SUITE = [
    {
        "id": "PARA_1",
        "effect": "text.paraphrase.semantic_preserving",
        "instruction": "Paraphrase the sentence without changing any facts. Use one sentence and no more than 24 words. Return only the answer.",
        "source": "Neris delivered seven amber parcels to Corin before sunrise on Tuesday.",
        "required_groups": [["neris"], ["corin"], ["seven", "7"], ["amber"], ["tuesday"]],
        "forbidden_exact": True,
        "max_words": 24,
        "max_sentences": 1,
        "min_source_change": True,
    },
    {
        "id": "PARA_2",
        "effect": "text.paraphrase.semantic_preserving",
        "instruction": "Paraphrase the sentence without changing any facts. Use one sentence and no more than 28 words. Return only the answer.",
        "source": "The observatory postponed the Lumen-4 launch by three days because high winds crossed the ridge.",
        "required_groups": [["lumen-4", "lumen 4"], ["three", "3"], ["wind"], ["ridge"], ["postpon", "delay"]],
        "forbidden_exact": True,
        "max_words": 28,
        "max_sentences": 1,
        "min_source_change": True,
    },
    {
        "id": "SIMPLE_1",
        "effect": "text.simplify.semantic_preserving",
        "instruction": "Rewrite this in simple everyday English in no more than 14 words. Preserve who did what and where. Return only the answer.",
        "source": "Following the cessation of precipitation, Mira initiated pedestrian transit toward the eastern laboratory.",
        "required_groups": [["mira"], ["east", "eastern"], ["lab", "laboratory"], ["walk", "went", "go", "headed", "moved", "travel"]],
        "max_words": 14,
        "min_source_change": True,
    },
    {
        "id": "SIMPLE_2",
        "effect": "text.simplify.semantic_preserving",
        "instruction": "Rewrite this in simple everyday English in no more than 18 words. Preserve the cause and action. Return only the answer.",
        "source": "Because the photovoltaic array ceased generating energy after dusk, Tovan activated the reserve battery.",
        "required_groups": [["tovan"], ["battery"], ["solar", "photovoltaic"], ["dusk", "night", "dark"], ["because", "so", "when", "after"]],
        "max_words": 18,
        "min_source_change": True,
    },
    {
        "id": "SUM_1",
        "effect": "text.summarize.faithful",
        "instruction": "Summarize the report in one sentence of no more than 22 words. Keep the mission result and return event. Return only the answer.",
        "source": "The Alba rover traveled twelve kilometers across the plain. Its battery fell to 41 percent. At Site K it collected a basalt sample. Alba returned to base at 18:20 without damage.",
        "required_groups": [["alba"], ["basalt"], ["site k", "site-k"], ["return", "base"], ["without damage", "undamaged", "safe"]],
        "max_words": 22,
        "max_sentences": 1,
    },
    {
        "id": "SUM_2",
        "effect": "text.summarize.faithful",
        "instruction": "Summarize the report in one sentence of no more than 22 words. Keep the decision, reason, and new time. Return only the answer.",
        "source": "The Delta team inspected Bridge 6 at 09:00. Engineers found ice on the north joints. The team postponed the load test for safety. The replacement test is scheduled for Friday at 14:00.",
        "required_groups": [["delta"], ["bridge 6", "bridge-6"], ["ice"], ["postpon", "delay"], ["friday"], ["14:00", "2:00", "2 pm", "2pm"]],
        "max_words": 22,
        "max_sentences": 1,
    },
    {
        "id": "STORY_1",
        "effect": "text.story.generate_instruction_grounded",
        "instruction": "Write exactly three short sentences. In order: Nara finds a brass key; she opens a green box with it; she gives the map inside to Ivo. Return only the story.",
        "source": "",
        "required_groups": [["nara"], ["brass"], ["key"], ["green"], ["box"], ["map"], ["ivo"]],
        "ordered_groups": [["nara", "key"], ["green", "box"], ["map", "ivo"]],
        "exact_sentences": 3,
        "max_words": 45,
    },
    {
        "id": "STORY_2",
        "effect": "text.story.generate_instruction_grounded",
        "instruction": "Write exactly three short sentences. In order: Aris lights a lantern; he crosses the old bridge; he uses the lantern to guide a lost dog home. Return only the story.",
        "source": "",
        "required_groups": [["aris"], ["lantern"], ["bridge"], ["dog"], ["home"]],
        "ordered_groups": [["aris", "lantern"], ["bridge"], ["dog", "home"]],
        "exact_sentences": 3,
        "max_words": 45,
    },
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def strip_permitted_generation_wrappers(text: str) -> str:
    """Apply only the post-generation normalization authorized by V2."""
    value = str(text)
    value = re.sub(r"<think>.*?</think>", "", value, flags=re.I | re.S)
    # Some templates can emit a stray closing think tag despite thinking=False.
    value = re.sub(r"^.*?</think>", "", value, flags=re.I | re.S)
    value = value.strip()
    value = re.sub(r"^(?:final(?: answer)?):\s*", "", value, count=1, flags=re.I)
    return value.strip()


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)


def sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]


def contains_group(text: str, group: list[str]) -> bool:
    low = normalize(text)
    return any(normalize(token) in low for token in group)


def ordered_groups_in_distinct_sentences(text: str, groups: list[list[str]]) -> bool:
    ss = sentences(text)
    next_index = 0
    for group in groups:
        found = None
        for i in range(next_index, len(ss)):
            low = normalize(ss[i])
            if all(normalize(token) in low for token in group):
                found = i
                break
        if found is None:
            return False
        next_index = found + 1
    return True


def exact_prompt(case: dict) -> str:
    if case["source"]:
        return case["instruction"] + SOURCE_SEPARATOR + case["source"]
    return case["instruction"]


def call_model(prompt: str, seed: int) -> tuple[str, dict]:
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 192,
        "seed": seed,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request = urllib.request.Request(
        SERVER,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        body = json.loads(response.read().decode("utf-8"))
    raw = str(body["choices"][0]["message"].get("content") or "")
    return raw, payload


def grade(case: dict, raw_answer: str) -> dict:
    answer = strip_permitted_generation_wrappers(raw_answer)
    checks: dict[str, bool] = {}

    checks["required_groups"] = all(
        contains_group(answer, group) for group in case.get("required_groups", [])
    )
    if "max_words" in case:
        checks["max_words"] = len(words(answer)) <= int(case["max_words"])
    if "max_sentences" in case:
        checks["max_sentences"] = len(sentences(answer)) <= int(case["max_sentences"])
    if "exact_sentences" in case:
        checks["exact_sentences"] = len(sentences(answer)) == int(case["exact_sentences"])
    if case.get("forbidden_exact"):
        checks["forbidden_exact"] = normalize(answer) != normalize(case["source"])
    if case.get("min_source_change"):
        checks["min_source_change"] = normalize(answer) != normalize(case["source"])
    if case.get("ordered_groups"):
        checks["ordered_groups"] = ordered_groups_in_distinct_sentences(
            answer, case["ordered_groups"]
        )
    checks["nonempty"] = bool(answer.strip())

    return {
        "id": case["id"],
        "effect": case["effect"],
        "pass": all(checks.values()),
        "checks": checks,
        "raw_answer": raw_answer,
        "answer": answer,
        "word_count": len(words(answer)),
        "sentence_count": len(sentences(answer)),
    }


def main() -> int:
    results = []
    prompts = []
    requests = []

    for index, case in enumerate(SUITE):
        prompt = exact_prompt(case)
        seed = BASE_SEED + index
        raw, payload = call_model(prompt, seed)
        result = grade(case, raw)
        result["seed"] = seed
        results.append(result)
        prompts.append({"id": case["id"], "prompt": prompt})
        requests.append({"id": case["id"], "payload": payload})
        print(json.dumps(result, ensure_ascii=False), flush=True)

    effects = sorted({case["effect"] for case in SUITE})
    effect_status = {
        effect: (
            len([r for r in results if r["effect"] == effect]) == 2
            and all(r["pass"] for r in results if r["effect"] == effect)
        )
        for effect in effects
    }
    suite_pass = len(results) == 8 and all(r["pass"] for r in results) and all(effect_status.values())

    receipt = {
        "schema": SCHEMA,
        "status": "PASS" if suite_pass else "FAIL",
        "date": "2026-10-04",
        "brain_precommit_commit": BRAIN_PRECOMMIT_COMMIT,
        "execution_subject": {
            "repository": "empero-ai/Qwen3.8-4B-Distill-GGUF",
            "revision": "391fc7d103e3942a408def3e4f51c2f85d464417",
            "file": "Qwen3.8-4B-Q4_K_M.gguf",
            "bytes": 2783446304,
            "sha256": "dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790",
        },
        "runtime": {
            "repository": "ggml-org/llama.cpp",
            "commit": "0504396140d1c882f5f6ee34466a42db7ae90114",
            "runner": "ubuntu-24.04",
            "threads": 4,
            "context_tokens": 4096,
            "parallel": 1,
        },
        "generation_policy": {
            "attempts_per_case": 1,
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": 192,
            "fixed_seed_base": BASE_SEED,
            "seed_schedule_rule": "SEED_EQUALS_424200_PLUS_ZERO_BASED_FROZEN_SUITE_INDEX",
            "adaptive_retry": False,
            "case_specific_tuning": False,
            "system_message": None,
            "source_separator_literal": SOURCE_SEPARATOR,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        "prompts": prompts,
        "requests": requests,
        "results": results,
        "case_count": len(results),
        "case_pass_count": sum(int(r["pass"]) for r in results),
        "effect_status": effect_status,
        "terminal_cases_consumed": 0,
        "new_terminal_cases_exposed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "interpretation": (
            "PASS qualifies only this exact model/runtime/prompt/seed configuration as a bounded "
            "nonterminal semantic-seed producer candidate for the four declared effects. FAIL "
            "falsifies that exact configuration for this frozen contract."
        ),
        "hard_nonclaims": [
            "NO_LIVEBENCH_THRESHOLD_SCORE_INHERITANCE",
            "NO_TERMINAL_CASE_CONTENT_OR_METADATA_USED",
            "NO_GENERAL_SEMANTIC_EQUIVALENCE_THEOREM",
            "NO_OPUS55_PARITY_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
            "NO_AUTHORIZATION_TO_CONSUME_CASE_73_OR_LATER",
        ],
    }

    Path("qwen38_4b_root1_semantic_seed_receipt_v2.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": receipt["status"],
        "case_pass_count": receipt["case_pass_count"],
        "effect_status": effect_status,
    }, sort_keys=True))
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
