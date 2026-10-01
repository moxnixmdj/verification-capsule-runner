#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import HfApi
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).resolve().parent
EPISODES_PATH = HERE / "episodes.json"
ROUTER_PATH = HERE / "cognitive_tool_router.py"
RESULT_PATH = HERE / "result.json"
MODEL_ID = "pipizhao/SkillRouter-Reranker-0.6B"

spec = importlib.util.spec_from_file_location("c3_router", ROUTER_PATH)
router = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = router
spec.loader.exec_module(router)

def lexical_scorer(query: str, descriptions: list[str]) -> list[float]:
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    out = []
    for text in descriptions:
        t = set(re.findall(r"[a-z0-9]+", text.lower()))
        out.append((len(q & t) / max(1, len(q | t))) if (q or t) else 0.0)
    return out

def execute(route_id: str, payload: dict[str, Any]) -> str:
    if route_id == "sum_numbers": return str(round(sum(payload["numbers"]), 10))
    if route_id == "mean_numbers": return str(float(sum(payload["numbers"]) / len(payload["numbers"])))
    if route_id == "median_numbers": return str(float(statistics.median(payload["numbers"])))
    if route_id == "max_number": return str(max(payload["numbers"]))
    if route_id == "sort_numbers": return ",".join(str(x) for x in sorted(payload["numbers"]))
    if route_id == "unique_items": return ",".join(dict.fromkeys(payload["items"]))
    if route_id == "sort_text": return ",".join(sorted(payload["items"]))
    if route_id == "count_words": return str(len(payload["text"].split()))
    if route_id == "count_lines": return str(len(payload["text"].splitlines()))
    if route_id == "uppercase_text": return payload["text"].upper()
    if route_id == "reverse_text": return payload["text"][::-1]
    if route_id == "basename_path": return os.path.basename(payload["path"])
    if route_id == "extension_path": return os.path.splitext(payload["path"])[1]
    if route_id == "json_key": return str(payload["object"][payload["key"]])
    if route_id == "km_to_miles": return f'{payload["km"] * 0.621371:.5f}'
    if route_id == "c_to_f": return str(float(payload["celsius"] * 9 / 5 + 32))
    if route_id == "sha256_text": return hashlib.sha256(payload["text"].encode()).hexdigest()
    if route_id == "dropbox_search": return "FOUND:" + payload["text"]
    if route_id == "drive_search": return "DRIVE:" + payload["text"]
    if route_id == "web_search": return "WEB:" + payload["text"]
    if route_id == "local_file_search": return "LOCAL:" + payload["text"]
    raise KeyError(route_id)

def run_episode(ep: dict[str, Any], scorer) -> dict[str, Any]:
    routes = [router.ToolRoute(**r) for r in ep["routes"]]
    t0 = time.perf_counter()
    decision = router.select_route(
        ep["query"],
        routes,
        scorer,
        required_provider=ep.get("required_provider"),
        allowed_route_ids=set(ep["allowed_route_ids"]) if ep.get("allowed_route_ids") else None,
    )
    route_ms = (time.perf_counter() - t0) * 1000.0
    expected_status = ep.get("expected_status", "SELECT")
    if decision.status == "ESCALATE":
        output = "ESCALATE"
        success = expected_status == "ESCALATE" and output == ep["expected_output"]
    else:
        try:
            output = execute(decision.route_id, ep["payload"])
        except Exception as exc:
            output = f"TOOL_ERROR:{type(exc).__name__}"
        success = (
            expected_status == "SELECT"
            and decision.route_id == ep.get("expected_route")
            and output == ep["expected_output"]
        )
    return {
        "id": ep["id"],
        "selected_route": decision.route_id,
        "decision_status": decision.status,
        "eligible_route_ids": list(decision.eligible_route_ids),
        "expected_route": ep.get("expected_route"),
        "expected_status": expected_status,
        "output": output,
        "expected_output": ep["expected_output"],
        "terminal_success": bool(success),
        "routing_latency_ms": route_ms,
        "semantic_choice_required": decision.status == "SELECT" and len(decision.eligible_route_ids) > 1,
    }

def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    semantic = [r for r in rows if r["semantic_choice_required"]]
    deterministic = [r for r in rows if not r["semantic_choice_required"]]
    return {
        "episodes": len(rows),
        "terminal_successes": sum(r["terminal_success"] for r in rows),
        "terminal_success_rate": sum(r["terminal_success"] for r in rows) / len(rows),
        "semantic_choice_episodes": len(semantic),
        "semantic_terminal_success_rate": (
            sum(r["terminal_success"] for r in semantic) / len(semantic) if semantic else None
        ),
        "deterministic_filter_episodes": len(deterministic),
        "deterministic_filter_success_rate": (
            sum(r["terminal_success"] for r in deterministic) / len(deterministic)
            if deterministic else None
        ),
        "mean_routing_latency_ms": sum(r["routing_latency_ms"] for r in rows) / len(rows),
        "failures": [r["id"] for r in rows if not r["terminal_success"]],
    }

def main() -> int:
    capsule = json.loads(EPISODES_PATH.read_text())
    episodes = capsule["episodes"]

    model_info = HfApi().model_info(MODEL_ID)
    revision = model_info.sha
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    ).eval()

    token_yes = tokenizer.convert_tokens_to_ids("yes")
    token_no = tokenizer.convert_tokens_to_ids("no")
    if token_yes == tokenizer.unk_token_id or token_no == tokenizer.unk_token_id:
        raise RuntimeError(f"yes/no token lookup failed: yes={token_yes} no={token_no}")

    prefix = (
        '<|im_start|>system\nJudge whether the Document meets the requirements '
        'based on the Query and the Instruct provided. Note that the answer can '
        'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
    )
    suffix = '<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
    prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)

    def skillrouter_scorer(query: str, descriptions: list[str]) -> list[float]:
        scores: list[float] = []
        instruction = (
            "Given a task description, judge whether the skill document "
            "is relevant and useful for completing the task"
        )
        for description in descriptions:
            prompt = (
                f"<Instruct>: {instruction}\n\n"
                f"<Query>: {query}\n\n"
                f"<Document>: {description}"
            )
            tokens = tokenizer(
                prompt,
                padding=False,
                truncation=True,
                max_length=2048 - len(prefix_tokens) - len(suffix_tokens),
                return_attention_mask=False,
            )["input_ids"]
            input_ids = torch.tensor([prefix_tokens + tokens + suffix_tokens])
            attention_mask = torch.ones_like(input_ids)
            with torch.no_grad():
                logits = model(input_ids=input_ids, attention_mask=attention_mask).logits[:, -1, :]
            scores.append(float((logits[:, token_yes] - logits[:, token_no]).item()))
        return scores

    baseline_rows = [run_episode(ep, lexical_scorer) for ep in episodes]
    skill_rows = [run_episode(ep, skillrouter_scorer) for ep in episodes]
    baseline = aggregate(baseline_rows)
    skill = aggregate(skill_rows)
    delta = skill["terminal_success_rate"] - baseline["terminal_success_rate"]
    semantic_delta = (
        skill["semantic_terminal_success_rate"] - baseline["semantic_terminal_success_rate"]
    )
    filter_safety = all(
        r["terminal_success"] for r in skill_rows
        if r["id"] in {
            "provider_filter_authorized",
            "provider_filter_unavailable",
            "provider_filter_unauthorized",
        }
    )
    result = {
        "schema": "PROJECT_BRAIN_C3_SKILLROUTER_SPENT_SCREEN_RESULT_V1",
        "status": "SPENT_EPISODE_SCREEN_ONLY__ZERO_CAPABILITY_CREDIT",
        "episodes_source_commit": "985483c8eb6695adf5c5b9cc292417fb4a65b9b5",
        "episodes_blob": "439a13dfd5824117e3d50a7a5673056cbc745dfd",
        "model": MODEL_ID,
        "model_revision": revision,
        "model_license": "Apache-2.0",
        "baseline": baseline,
        "skillrouter": skill,
        "terminal_success_delta": delta,
        "semantic_terminal_success_delta": semantic_delta,
        "deterministic_provider_filter_safety_pass": filter_safety,
        "fresh_evidence_authorized": bool(
            filter_safety
            and skill["terminal_success_rate"] > baseline["terminal_success_rate"]
            and skill["semantic_terminal_success_rate"] > baseline["semantic_terminal_success_rate"]
        ),
        "baseline_rows": baseline_rows,
        "skillrouter_rows": skill_rows,
        "capability_credit_delta": 0,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    summary = {k:v for k,v in result.items() if not k.endswith("_rows")}
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
