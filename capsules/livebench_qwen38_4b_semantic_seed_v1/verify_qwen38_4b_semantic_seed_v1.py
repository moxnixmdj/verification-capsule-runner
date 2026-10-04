#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PRECOMMIT = HERE / "canonical/governance/LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V1.json"
RECEIPT = HERE / "LIVEBENCH_QWEN38_4B_SEMANTIC_SEED_PUBLIC_VERIFICATION_V1.json"

URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "brain-qwen3.8-4b"


def norm(text: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(text or ""))
        .lower()
        .replace("’", "'")
        .split()
    )


def semantic_surface(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", norm(text)))


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w°'-]+\b", unicodedata.normalize("NFKC", text), flags=re.UNICODE)


def sentence_count(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", stripped) if p.strip()]
    return len(parts)


def strip_optional_think(text: str) -> str:
    out = str(text or "").strip()
    out = re.sub(r"(?is)^\s*<think>.*?</think>\s*", "", out).strip()
    return out


def any_alt(text: str, alternatives: list[str]) -> bool:
    low = norm(text)
    return any(norm(x) in low for x in alternatives)


def first_pos(text: str, token: str) -> int:
    return norm(text).find(norm(token))


def ordered_event_groups(text: str, groups: list[list[str]]) -> bool:
    low = norm(text)
    previous_end = -1
    for group in groups:
        positions = []
        for token in group:
            p = low.find(norm(token))
            if p < 0:
                return False
            positions.append((p, p + len(norm(token))))
        event_start = min(p for p, _ in positions)
        event_end = max(e for _, e in positions)
        if event_start <= previous_end:
            return False
        previous_end = event_end
    return True


def chat(prompt: str, *, seed: int, temperature: float, top_p: float, max_tokens: int) -> tuple[str, dict]:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "top_p": top_p,
        "seed": seed,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        if int(getattr(response, "status", 200)) != 200:
            raise RuntimeError(f"HTTP_STATUS:{getattr(response, 'status', None)}")
        raw = response.read(500_001)
    if len(raw) > 500_000:
        raise RuntimeError("RESPONSE_TOO_LARGE")
    data = json.loads(raw.decode("utf-8", "replace"))
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise RuntimeError("ONE_CHOICE_REQUIRED")
    message = (choices[0] or {}).get("message")
    if not isinstance(message, dict):
        raise RuntimeError("MESSAGE_REQUIRED")
    if message.get("tool_calls"):
        raise RuntimeError("UNEXPECTED_TOOL_CALL")
    content = strip_optional_think(str(message.get("content") or ""))
    if not content:
        raise RuntimeError("NONEMPTY_FINAL_CONTENT_REQUIRED")
    return content, data


def validate(case: dict, output: str) -> tuple[bool, list[str], dict]:
    failures: list[str] = []
    wc = len(words(output))
    sc = sentence_count(output)
    metrics = {"word_count": wc, "sentence_count": sc}

    for i, group in enumerate(case.get("required_groups") or []):
        if not any_alt(output, group):
            failures.append(f"REQUIRED_GROUP_MISSING:{i}:{group}")

    if case.get("ordered_groups"):
        if not ordered_event_groups(output, case["ordered_groups"]):
            failures.append("ORDERED_EVENT_GROUPS_FAIL")

    source = str(case.get("source") or "")
    if case.get("forbidden_exact") and norm(output) == norm(source):
        failures.append("FORBIDDEN_EXACT_COPY")

    if case.get("min_source_change") and source:
        if semantic_surface(output) == semantic_surface(source):
            failures.append("MIN_SOURCE_CHANGE_FAIL")

    if "max_words" in case and wc > int(case["max_words"]):
        failures.append(f"MAX_WORDS_FAIL:{wc}>{case['max_words']}")

    if "max_sentences" in case and sc > int(case["max_sentences"]):
        failures.append(f"MAX_SENTENCES_FAIL:{sc}>{case['max_sentences']}")

    if "exact_sentences" in case and sc != int(case["exact_sentences"]):
        failures.append(f"EXACT_SENTENCES_FAIL:{sc}!={case['exact_sentences']}")

    if norm(output).startswith(("as an ai", "i cannot", "i can't", "here is an explanation")):
        failures.append("META_OR_REFUSAL_OUTPUT")

    return not failures, failures, metrics


def main() -> int:
    doc = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
    assert doc["schema"] == "PROJECT_BRAIN_LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V1"
    assert doc["status"].startswith("PRECOMMITTED__")
    assert doc["accounting"]["new_terminal_cases_exposed"] == 0
    subject = doc["execution_subject"]
    runtime = doc["runtime"]
    policy = doc["generation_policy"]
    suite = doc["frozen_nonterminal_suite"]

    assert len(suite) == 8
    assert policy["attempts_per_case"] == 1
    assert policy["adaptive_retry"] is False
    assert policy["case_specific_tuning"] is False

    results = []
    passed = 0
    effect_counts: dict[str, dict[str, int]] = {}

    for i, case in enumerate(suite):
        prompt = str(case["instruction"])
        source = str(case.get("source") or "")
        if source:
            prompt += "\n\nSOURCE:\n" + source
        seed = int(policy["fixed_seed_base"]) + i
        try:
            output, raw = chat(
                prompt,
                seed=seed,
                temperature=float(policy["temperature"]),
                top_p=float(policy["top_p"]),
                max_tokens=int(policy["max_tokens"]),
            )
            ok, failures, metrics = validate(case, output)
            model_reported = str(raw.get("model") or "")
            if model_reported and model_reported != MODEL:
                failures.append(f"MODEL_ALIAS_MISMATCH:{model_reported}")
                ok = False
            if ok:
                passed += 1
            row = {
                "id": case["id"],
                "effect": case["effect"],
                "status": "PASS" if ok else "FAIL",
                "seed": seed,
                "failures": failures,
                "metrics": metrics,
                "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                "output": output,
            }
        except Exception as exc:
            row = {
                "id": case["id"],
                "effect": case["effect"],
                "status": "ERROR",
                "seed": seed,
                "failures": [f"{type(exc).__name__}:{exc}"],
            }
        results.append(row)
        ec = effect_counts.setdefault(case["effect"], {"passed": 0, "required": 0})
        ec["required"] += 1
        if row["status"] == "PASS":
            ec["passed"] += 1

    full_pass = passed == len(suite) and all(v["passed"] == v["required"] for v in effect_counts.values())
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_QWEN38_4B_SEMANTIC_SEED_PUBLIC_VERIFICATION_V1",
        "date": "2026-10-04",
        "status": "PASS" if full_pass else "FAIL",
        "subject": {
            "brain_precommit_blob": "49dad45f14b4afa81799cc0e3dcb18293ab2fca9",
            "repository": subject["repository"],
            "revision": subject["revision"],
            "file": subject["file"],
            "bytes": subject["bytes"],
            "sha256": subject["sha256"],
            "license": subject["license"],
        },
        "runtime": {
            "repository": runtime["repository"],
            "commit": runtime["commit"],
            "endpoint": URL,
            "loopback_only": True,
            "threads": runtime["threads"],
            "context_tokens": runtime["context_tokens"],
        },
        "generation_policy": policy,
        "terminal_case_exposure": 0,
        "terminal_results_observed": 0,
        "passed": passed,
        "required": len(suite),
        "per_effect": effect_counts,
        "results": results,
        "consequence_if_pass": [
            "EXACT_2_783GB_QWEN38_4B_Q4_K_M_SUBJECT_IS_A_BOUNDED_NONTERMINAL_SEMANTIC_SEED_PRODUCER_CANDIDATE",
            "SEMANTIC_SEED_SUBSTRATE_CANDIDATE_SIZE_DROPS_BELOW_THE_EXISTING_5_060GB_QWEN35_9B_ROUTE",
            "NEXT_CAUSAL_STEP_IS_SAME_PROTOCOL_RAW_SUBSTRATE_NEGATIVE_CONTROL_VERSUS_BRAIN_CONFIGURED_POSITIVE_CONTROL"
        ] if full_pass else [],
        "hard_nonclaims": doc["hard_nonclaims"] + [
            "NO_STANDALONE_LIVEBENCH_IF_NEGATIVE_CONTROL_HAS_BEEN_PROVED_FOR_THIS_4B_SUBJECT",
            "NO_OWNERSHIP_CREDIT_FROM_SEMANTIC_SEED_QUALIFICATION_ALONE"
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "passed": passed,
        "required": len(suite),
        "per_effect": effect_counts,
        "receipt": str(RECEIPT),
    }, sort_keys=True))
    return 0 if full_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
