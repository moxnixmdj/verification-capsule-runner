#!/usr/bin/env python3
# Execution trigger: 2026-10-04 canonical Root1 resource-minimum qualification; verifier logic unchanged.
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_QWEN38_4B_ROOT1_SEMANTIC_SEED_PUBLIC_VERIFICATION_V1"
SERVER = "http://127.0.0.1:8080/v1/chat/completions"
BASE_SEED = 424200

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


def strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def call_model(prompt: str, seed: int) -> str:
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 192,
        "seed": seed,
        "stream": False,
    }
    req = urllib.request.Request(
        SERVER,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return str(body["choices"][0]["message"].get("content") or "")


def score_case(case: dict, answer: str) -> dict:
    clean = strip_think(answer)
    low = clean.lower()
    checks: dict[str, bool] = {}

    for idx, group in enumerate(case.get("required_groups", []), 1):
        checks[f"required_group_{idx}"] = any(token.lower() in low for token in group)

    if "max_words" in case:
        checks["max_words"] = len(words(clean)) <= int(case["max_words"])
    if "max_sentences" in case:
        checks["max_sentences"] = len(sentences(clean)) <= int(case["max_sentences"])
    if "exact_sentences" in case:
        checks["exact_sentences"] = len(sentences(clean)) == int(case["exact_sentences"])
    if case.get("forbidden_exact"):
        checks["forbidden_exact"] = normalized(clean) != normalized(case["source"])
    if case.get("min_source_change"):
        checks["min_source_change"] = normalized(clean) != normalized(case["source"])

    ordered = case.get("ordered_groups") or []
    if ordered:
        ss = sentences(clean)
        positions: list[int] = []
        start = 0
        ok = True
        for group in ordered:
            found = None
            for idx in range(start, len(ss)):
                sl = ss[idx].lower()
                if all(token.lower() in sl for token in group):
                    found = idx
                    break
            if found is None:
                ok = False
                break
            positions.append(found)
            start = found + 1
        checks["ordered_groups"] = ok

    checks["nonempty"] = bool(clean.strip())
    passed = all(checks.values())
    return {
        "id": case["id"],
        "effect": case["effect"],
        "passed": passed,
        "checks": checks,
        "answer": clean,
        "word_count": len(words(clean)),
        "sentence_count": len(sentences(clean)),
    }


def main() -> int:
    results = []
    for idx, case in enumerate(SUITE):
        prompt = case["instruction"]
        if case["source"]:
            prompt += "\n\nText:\n" + case["source"]
        raw = call_model(prompt, BASE_SEED + idx)
        result = score_case(case, raw)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    effect_status: dict[str, bool] = {}
    for effect in sorted({x["effect"] for x in SUITE}):
        rows = [r for r in results if r["effect"] == effect]
        effect_status[effect] = len(rows) == 2 and all(r["passed"] for r in rows)

    suite_pass = len(results) == 8 and all(r["passed"] for r in results) and all(effect_status.values())
    receipt = {
        "schema": SCHEMA,
        "status": "PASS" if suite_pass else "FAIL",
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
            "adaptive_retry": False,
        },
        "case_count": len(results),
        "case_pass_count": sum(1 for r in results if r["passed"]),
        "effect_status": effect_status,
        "results": results,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "NO_LIVEBENCH_THRESHOLD_SCORE_INHERITANCE",
            "NO_TERMINAL_CASE_CONTENT_OR_METADATA_USED",
            "BOUNDED_SYNTHETIC_SEMANTIC_SEED_PASS_IS_NOT_A_GENERAL_SEMANTIC_EQUIVALENCE_THEOREM",
            "NO_ACCEPTANCE_FAMILY_OR_TERMINAL_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    out = Path("qwen38_4b_root1_semantic_seed_receipt.json")
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "case_pass_count": receipt["case_pass_count"], "effect_status": effect_status}, sort_keys=True))
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
