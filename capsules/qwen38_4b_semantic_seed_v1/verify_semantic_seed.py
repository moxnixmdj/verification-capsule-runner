#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = json.loads((ROOT / "LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V1.json").read_text(encoding="utf-8"))
ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "brain-qwen3.8-4b"
POLICY = SPEC["generation_policy"]


def strip_think(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"(?is)<think>.*?</think>\s*", "", text)
    text = re.sub(r"(?is)^.*?</think>\s*", "", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)


def sentence_chunks(text: str) -> list[str]:
    chunks = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    return chunks if chunks else ([text.strip()] if text.strip() else [])


def has_group(text: str, group: list[str]) -> bool:
    low = text.casefold()
    return any(str(token).casefold() in low for token in group)


def api(prompt: str, seed: int) -> tuple[str, float]:
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Follow the user's visible transformation request exactly. Return only the final requested text. Do not explain your reasoning."
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": POLICY["temperature"],
        "top_p": POLICY["top_p"],
        "max_tokens": POLICY["max_tokens"],
        "seed": seed,
        "stream": False,
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read(500_000).decode("utf-8", "replace"))
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise RuntimeError("ONE_CHOICE_REQUIRED")
    content = strip_think((choices[0].get("message") or {}).get("content", ""))
    if not content:
        raise RuntimeError("NONEMPTY_FINAL_REQUIRED")
    return content, round(time.monotonic() - t0, 3)


def score_case(case: dict, response: str) -> dict:
    checks: dict[str, bool] = {}
    checks["nonempty"] = bool(response.strip())
    checks["required_groups"] = all(has_group(response, g) for g in case.get("required_groups", []))

    source = str(case.get("source") or "").strip()
    if case.get("forbidden_exact"):
        checks["not_exact_source"] = response.strip().casefold() != source.casefold()
    if case.get("min_source_change") and source:
        checks["source_changed"] = response.strip().casefold() != source.casefold()

    wc = len(words(response))
    if case.get("max_words") is not None:
        checks["max_words"] = wc <= int(case["max_words"])

    sentences = sentence_chunks(response)
    if case.get("max_sentences") is not None:
        checks["max_sentences"] = len(sentences) <= int(case["max_sentences"])
    if case.get("exact_sentences") is not None:
        checks["exact_sentences"] = len(sentences) == int(case["exact_sentences"])

    ordered = case.get("ordered_groups") or []
    if ordered:
        # The frozen stories request the three events in order. Require each declared
        # event group to be fully present in the corresponding sentence. This is
        # stronger than merely checking global token order.
        ordered_ok = len(sentences) >= len(ordered)
        if ordered_ok:
            for i, group in enumerate(ordered):
                low = sentences[i].casefold()
                if not all(str(token).casefold() in low for token in group):
                    ordered_ok = False
                    break
        checks["ordered_events"] = ordered_ok

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "word_count": wc,
        "sentence_count": len(sentences),
    }


rows = []
for index, case in enumerate(SPEC["frozen_nonterminal_suite"]):
    prompt = case["instruction"]
    if str(case.get("source") or "").strip():
        prompt += "\n\nText to transform:\n" + case["source"]
    response, duration = api(prompt, int(POLICY["fixed_seed_base"]) + index)
    result = score_case(case, response)
    row = {
        "id": case["id"],
        "effect": case["effect"],
        "response": response,
        "duration_s": duration,
        **result,
    }
    rows.append(row)
    print(json.dumps({"progress": row}, ensure_ascii=False), file=sys.stderr, flush=True)

effect_rows: dict[str, list[dict]] = {}
for row in rows:
    effect_rows.setdefault(row["effect"], []).append(row)
effect_pass = {effect: len(items) == 2 and all(x["passed"] for x in items) for effect, items in effect_rows.items()}

receipt = {
    "schema": "PROJECT_BRAIN_QWEN38_4B_SEMANTIC_SEED_PUBLIC_RUNNER_RECEIPT_V1",
    "status": "PASS" if len(rows) == 8 and all(x["passed"] for x in rows) and all(effect_pass.values()) else "FAIL",
    "subject": {
        "repository": SPEC["execution_subject"]["repository"],
        "revision": SPEC["execution_subject"]["revision"],
        "file": SPEC["execution_subject"]["file"],
        "bytes": SPEC["execution_subject"]["bytes"],
        "sha256": SPEC["execution_subject"]["sha256"],
        "llama_cpp_commit": SPEC["runtime"]["commit"],
    },
    "generation_policy": POLICY,
    "cases": rows,
    "effect_pass": effect_pass,
    "passed_cases": sum(int(x["passed"]) for x in rows),
    "required_cases": 8,
    "terminal_case_exposure": 0,
    "terminal_prompt_exposure": 0,
    "incremental_spend_usd": 0,
}
print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
if receipt["status"] != "PASS":
    raise SystemExit(1)
