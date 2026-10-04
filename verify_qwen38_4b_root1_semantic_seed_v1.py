#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

MODEL = pathlib.Path(os.environ.get("MODEL_PATH", "Qwen3.8-4B-Q4_K_M.gguf"))
SERVER = pathlib.Path(os.environ.get("LLAMA_SERVER", "llama.cpp/build/bin/llama-server"))
MODEL_BYTES = 2_783_446_304
MODEL_SHA256 = "dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790"
PORT = 8080

CASES = [
    {
        "id": "PARA_1",
        "instruction": "Paraphrase the sentence without changing any facts. Use one sentence and no more than 24 words. Return only the answer.",
        "source": "Neris delivered seven amber parcels to Corin before sunrise on Tuesday.",
        "required_groups": [["neris"], ["corin"], ["seven", "7"], ["amber"], ["tuesday"]],
        "forbidden_exact": True, "max_words": 24, "max_sentences": 1, "min_source_change": True,
    },
    {
        "id": "PARA_2",
        "instruction": "Paraphrase the sentence without changing any facts. Use one sentence and no more than 28 words. Return only the answer.",
        "source": "The observatory postponed the Lumen-4 launch by three days because high winds crossed the ridge.",
        "required_groups": [["lumen-4", "lumen 4"], ["three", "3"], ["wind"], ["ridge"], ["postpon", "delay"]],
        "forbidden_exact": True, "max_words": 28, "max_sentences": 1, "min_source_change": True,
    },
    {
        "id": "SIMPLE_1",
        "instruction": "Rewrite this in simple everyday English in no more than 14 words. Preserve who did what and where. Return only the answer.",
        "source": "Following the cessation of precipitation, Mira initiated pedestrian transit toward the eastern laboratory.",
        "required_groups": [["mira"], ["east", "eastern"], ["lab", "laboratory"], ["walk", "went", "go", "headed", "moved", "travel"]],
        "max_words": 14, "min_source_change": True,
    },
    {
        "id": "SIMPLE_2",
        "instruction": "Rewrite this in simple everyday English in no more than 18 words. Preserve the cause and action. Return only the answer.",
        "source": "Because the photovoltaic array ceased generating energy after dusk, Tovan activated the reserve battery.",
        "required_groups": [["tovan"], ["battery"], ["solar", "photovoltaic"], ["dusk", "night", "dark"], ["because", "so", "when", "after"]],
        "max_words": 18, "min_source_change": True,
    },
    {
        "id": "SUM_1",
        "instruction": "Summarize the report in one sentence of no more than 22 words. Keep the mission result and return event. Return only the answer.",
        "source": "The Alba rover traveled twelve kilometers across the plain. Its battery fell to 41 percent. At Site K it collected a basalt sample. Alba returned to base at 18:20 without damage.",
        "required_groups": [["alba"], ["basalt"], ["site k", "site-k"], ["return", "base"], ["without damage", "undamaged", "safe"]],
        "max_words": 22, "max_sentences": 1,
    },
    {
        "id": "SUM_2",
        "instruction": "Summarize the report in one sentence of no more than 22 words. Keep the decision, reason, and new time. Return only the answer.",
        "source": "The Delta team inspected Bridge 6 at 09:00. Engineers found ice on the north joints. The team postponed the load test for safety. The replacement test is scheduled for Friday at 14:00.",
        "required_groups": [["delta"], ["bridge 6", "bridge-6"], ["ice"], ["postpon", "delay"], ["friday"], ["14:00", "2:00", "2 pm", "2pm"]],
        "max_words": 22, "max_sentences": 1,
    },
    {
        "id": "STORY_1",
        "instruction": "Write exactly three short sentences. In order: Nara finds a brass key; she opens a green box with it; she gives the map inside to Ivo. Return only the story.",
        "source": "",
        "required_groups": [["nara"], ["brass"], ["key"], ["green"], ["box"], ["map"], ["ivo"]],
        "ordered_groups": [["nara", "key"], ["green", "box"], ["map", "ivo"]],
        "exact_sentences": 3, "max_words": 45,
    },
    {
        "id": "STORY_2",
        "instruction": "Write exactly three short sentences. In order: Aris lights a lantern; he crosses the old bridge; he uses the lantern to guide a lost dog home. Return only the story.",
        "source": "",
        "required_groups": [["aris"], ["lantern"], ["bridge"], ["dog"], ["home"]],
        "ordered_groups": [["aris", "lantern"], ["bridge"], ["dog", "home"]],
        "exact_sentences": 3, "max_words": 45,
    },
]

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def strip_reasoning(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.I | re.S)
    text = re.sub(r"^\s*(?:final answer|answer)\s*:\s*", "", text, flags=re.I)
    return text.strip()

def words(text: str) -> list[str]:
    return re.findall(r"\b[\w-]+\b", text, flags=re.UNICODE)

def sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]

def contains_any(text: str, group: list[str]) -> bool:
    low = text.casefold()
    return any(term.casefold() in low for term in group)

def score_case(case: dict, answer: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    low = answer.casefold()
    for group in case.get("required_groups", []):
        if not contains_any(answer, group):
            failures.append("MISSING_GROUP:" + "|".join(group))
    if case.get("forbidden_exact") and answer.strip().casefold() == case.get("source", "").strip().casefold():
        failures.append("EXACT_COPY_FORBIDDEN")
    if case.get("min_source_change") and answer.strip().casefold() == case.get("source", "").strip().casefold():
        failures.append("SOURCE_CHANGE_REQUIRED")
    wc = len(words(answer))
    if "max_words" in case and wc > case["max_words"]:
        failures.append(f"WORDS_{wc}_GT_{case['max_words']}")
    ss = sentences(answer)
    if "max_sentences" in case and len(ss) > case["max_sentences"]:
        failures.append(f"SENTENCES_{len(ss)}_GT_{case['max_sentences']}")
    if "exact_sentences" in case and len(ss) != case["exact_sentences"]:
        failures.append(f"SENTENCES_{len(ss)}_NE_{case['exact_sentences']}")
    ordered = case.get("ordered_groups")
    if ordered:
        if len(ss) != len(ordered):
            failures.append("ORDER_SENTENCE_COUNT_MISMATCH")
        else:
            for i, group in enumerate(ordered):
                for term in group:
                    if term.casefold() not in ss[i].casefold():
                        failures.append(f"ORDER_{i+1}_MISSING:{term}")
    return (not failures), failures

def request_json(url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def wait_ready() -> None:
    deadline = time.time() + 180
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as e:
            last = repr(e)
        time.sleep(2)
    raise RuntimeError("SERVER_NOT_READY:" + str(last))

def main() -> int:
    assert MODEL.is_file(), MODEL
    assert MODEL.stat().st_size == MODEL_BYTES, (MODEL.stat().st_size, MODEL_BYTES)
    digest = sha256_file(MODEL)
    assert digest == MODEL_SHA256, digest
    assert SERVER.is_file(), SERVER

    log = open("qwen38_4b_server.log", "w", encoding="utf-8")
    cmd = [
        str(SERVER), "-m", str(MODEL), "-c", "4096", "-t", "4",
        "--host", "127.0.0.1", "--port", str(PORT), "-ngl", "0",
        "--no-webui",
    ]
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    try:
        wait_ready()
        results = []
        for i, case in enumerate(CASES):
            user = case["instruction"]
            if case.get("source"):
                user += "\n\nText:\n" + case["source"]
            payload = {
                "model": "local",
                "messages": [{"role": "user", "content": user}],
                "temperature": 0.6,
                "top_p": 0.95,
                "seed": 424200 + i,
                "max_tokens": 192,
                "stream": False,
            }
            raw = request_json(f"http://127.0.0.1:{PORT}/v1/chat/completions", payload)
            message = raw["choices"][0]["message"]
            content = message.get("content") or ""
            if not content and message.get("reasoning_content"):
                content = message.get("reasoning_content") or ""
            answer = strip_reasoning(content)
            passed, failures = score_case(case, answer)
            row = {
                "id": case["id"], "pass": passed, "failures": failures,
                "answer": answer, "word_count": len(words(answer)),
                "sentence_count": len(sentences(answer)),
            }
            results.append(row)
            print(json.dumps(row, ensure_ascii=False))
        suite_pass = all(r["pass"] for r in results)
        summary = {
            "schema": "PROJECT_BRAIN_QWEN38_4B_ROOT1_SEMANTIC_SEED_PUBLIC_RUNNER_RESULT_V1",
            "model_bytes": MODEL_BYTES,
            "model_sha256": MODEL_SHA256,
            "cases_passed": sum(r["pass"] for r in results),
            "cases_total": len(results),
            "suite_pass": suite_pass,
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "capability_credit": 0,
            "hard_nonclaim": "BOUNDED_NONTERMINAL_SUITE_PASS_IS_NOT_LIVEBENCH_THRESHOLD_OR_TERMINAL_CAPABILITY_CREDIT",
        }
        pathlib.Path("qwen38_4b_semantic_seed_result.json").write_text(
            json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, sort_keys=True))
        return 0 if suite_pass else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()

if __name__ == "__main__":
    raise SystemExit(main())
