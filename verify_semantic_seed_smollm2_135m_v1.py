#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRE = ROOT / "SEMANTIC_SEED_SMOLLM2_135M_PREEXPOSURE_V1.json"
OUT = ROOT / "semantic_seed_smollm2_135m_receipt.json"
API = "http://127.0.0.1:8080/v1/chat/completions"


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9.]+", text.lower())


def contains_group(text: str, group: list[str]) -> bool:
    low = text.lower()
    return any(str(x).lower() in low for x in group)


def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def source_ngram_recall(source: str, output: str, n: int = 4) -> float:
    src = ngrams(words(source), n)
    if not src:
        return 0.0
    out = Counter(ngrams(words(output), n))
    matched = 0
    for gram in src:
        if out[gram] > 0:
            matched += 1
            out[gram] -= 1
    return matched / len(src)


def call_model(system_prompt: str, instruction: str, temperature: float, max_tokens: int) -> str:
    body = json.dumps({
        "model": "local",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = json.loads(r.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"].strip()


def evaluate(task: dict, output: str) -> dict:
    wc = len(words(output))
    required = {
        "|".join(group): contains_group(output, group)
        for group in task.get("required_groups", [])
    }
    forbidden = {
        "|".join(group): contains_group(output, group)
        for group in task.get("forbidden_groups", [])
    }
    failures = []
    for label, ok in required.items():
        if not ok:
            failures.append("MISSING:" + label)
    for label, hit in forbidden.items():
        if hit:
            failures.append("FORBIDDEN:" + label)
    if wc < int(task.get("min_words", 0)):
        failures.append("TOO_SHORT")
    if wc > int(task.get("max_words", 10**9)):
        failures.append("TOO_LONG")
    overlap = None
    if "max_source_4gram_recall" in task:
        overlap = source_ngram_recall(task["source"], output, 4)
        if overlap > float(task["max_source_4gram_recall"]):
            failures.append("INSUFFICIENT_REWORDING")
    return {
        "pass": not failures,
        "word_count": wc,
        "required": required,
        "forbidden": forbidden,
        "source_4gram_recall": overlap,
        "failures": failures,
    }


def main() -> int:
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    assert pre["status"] == "FROZEN_BEFORE_MODEL_OUTPUTS__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT"
    gen = pre["generation"]
    rows = []
    family = Counter()
    t0 = time.perf_counter()
    for task in pre["tasks"]:
        start = time.perf_counter()
        output = call_model(gen["system_prompt"], task["instruction"], gen["temperature"], gen["max_tokens"])
        verdict = evaluate(task, output)
        if verdict["pass"]:
            family[task["family"]] += 1
        rows.append({
            "id": task["id"],
            "family": task["family"],
            "output": output,
            "evaluation": verdict,
            "wall_clock_seconds": time.perf_counter() - start,
        })

    total = sum(1 for r in rows if r["evaluation"]["pass"])
    rule = pre["decision_rule"]
    family_ok = all(family[f] >= int(rule["minimum_passes_per_family"]) for f in rule["families"])
    passed = total >= int(rule["minimum_total_passes"]) and family_ok
    model_path = Path("smollm2-135m-instruct-q4_0.gguf")
    observed_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    receipt = {
        "schema": "PROJECT_BRAIN_SEMANTIC_SEED_SMOLLM2_135M_INDEPENDENT_RESULT_V1",
        "status": rule["pass_label"] if passed else rule["fail_label"],
        "preexposure_sha256": hashlib.sha256(PRE.read_bytes()).hexdigest(),
        "model_sha256_expected": pre["candidate"]["sha256"],
        "model_sha256_observed": observed_sha,
        "model_hash_match": observed_sha == pre["candidate"]["sha256"],
        "task_passes": total,
        "task_count": len(rows),
        "family_passes": dict(family),
        "family_floor_met": family_ok,
        "decision_rule_met": passed,
        "tasks": rows,
        "total_wall_clock_seconds": time.perf_counter() - t0,
        "persistent_learned_bytes_tested": model_path.stat().st_size,
        "external_frontier_model_calls": 0,
        "terminal_cases_consumed": 0,
        "hard_nonclaims": pre["hard_nonclaims"],
        "accounting": pre["accounting"],
    }
    assert receipt["model_hash_match"], receipt
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
