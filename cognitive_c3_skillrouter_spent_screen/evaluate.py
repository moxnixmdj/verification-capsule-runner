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

ROOT = Path(__file__).resolve().parent.parent
ROUTER_PATH = ROOT / "cognitive_c3_filtered_probe" / "cognitive_tool_router.py"
EPISODES_PATH = ROOT / "cognitive_c3_terminal_delta" / "episodes.json"
RESULT_PATH = Path(__file__).with_name("result.json")
MODEL_ID = "pipizhao/SkillRouter-Reranker-0.6B"

spec = importlib.util.spec_from_file_location("c3_router_skillrouter", ROUTER_PATH)
router = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = router
spec.loader.exec_module(router)

RERANK_INSTRUCTION = (
    "Given a coding task description, judge whether the skill document "
    "is relevant and useful for completing the task"
)

def lexical_scorer(query: str, descriptions: list[str]) -> list[float]:
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    out = []
    for text in descriptions:
        t = set(re.findall(r"[a-z0-9]+", text.lower()))
        out.append((len(q & t) / max(1, len(q | t))) if (q or t) else 0.0)
    return out

def execute(route_id: str, payload: dict[str, Any]) -> str:
    if route_id == "sum_numbers":
        return str(round(sum(payload["numbers"]), 10))
    if route_id == "mean_numbers":
        return str(float(sum(payload["numbers"]) / len(payload["numbers"])))
    if route_id == "median_numbers":
        return str(float(statistics.median(payload["numbers"])))
    if route_id == "max_number":
        return str(max(payload["numbers"]))
    if route_id == "sort_numbers":
        return ",".join(str(x) for x in sorted(payload["numbers"]))
    if route_id == "unique_items":
        return ",".join(dict.fromkeys(payload["items"]))
    if route_id == "sort_text":
        return ",".join(sorted(payload["items"]))
    if route_id == "count_words":
        return str(len(payload["text"].split()))
    if route_id == "count_lines":
        return str(len(payload["text"].splitlines()))
    if route_id == "uppercase_text":
        return payload["text"].upper()
    if route_id == "reverse_text":
        return payload["text"][::-1]
    if route_id == "basename_path":
        return os.path.basename(payload["path"])
    if route_id == "extension_path":
        return os.path.splitext(payload["path"])[1]
    if route_id == "json_key":
        return str(payload["object"][payload["key"]])
    if route_id == "km_to_miles":
        return f'{payload["km"] * 0.621371:.5f}'
    if route_id == "c_to_f":
        return str(float(payload["celsius"] * 9 / 5 + 32))
    if route_id == "sha256_text":
        return hashlib.sha256(payload["text"].encode()).hexdigest()
    if route_id == "dropbox_search":
        return "FOUND:" + payload["text"]
    if route_id == "drive_search":
        return "DRIVE:" + payload["text"]
    if route_id == "web_search":
        return "WEB:" + payload["text"]
    if route_id == "local_file_search":
        return "LOCAL:" + payload["text"]
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
        terminal_success = expected_status == "ESCALATE" and output == ep["expected_output"]
    else:
        try:
            output = execute(decision.route_id, ep["payload"])
        except Exception as exc:
            output = f"TOOL_ERROR:{type(exc).__name__}"
        terminal_success = (
            expected_status == "SELECT"
            and decision.route_id == ep.get("expected_route")
            and output == ep["expected_output"]
        )
    return {
        "id": ep["id"],
        "decision_status": decision.status,
        "selected_route": decision.route_id,
        "eligible_route_ids": list(decision.eligible_route_ids),
        "expected_route": ep.get("expected_route"),
        "expected_status": expected_status,
        "output": output,
        "expected_output": ep["expected_output"],
        "terminal_success": bool(terminal_success),
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

def format_rerank_prompt(route_id: str, description: str, query_text: str) -> str:
    doc_text = f"{route_id} | {description} | {description}"
    return (
        f"<Instruct>: {RERANK_INSTRUCTION}\n\n"
        f"<Query>: {query_text}\n\n"
        f"<Document>: {doc_text}"
    )

def get_template_tokens(tokenizer):
    prefix = (
        '<|im_start|>system\nJudge whether the Document meets the requirements '
        'based on the Query and the Instruct provided. Note that the answer can '
        'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
    )
    suffix = '<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
    return (
        tokenizer.encode(prefix, add_special_tokens=False),
        tokenizer.encode(suffix, add_special_tokens=False),
    )

def main() -> int:
    episodes = json.loads(EPISODES_PATH.read_text())["episodes"]
    model_info = HfApi().model_info(MODEL_ID)
    revision = model_info.sha

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=revision, padding_side="left", trust_remote_code=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, revision=revision, trust_remote_code=True, torch_dtype=torch.float32
    ).to("cpu").eval()
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    prefix_tokens, suffix_tokens = get_template_tokens(tokenizer)
    yes_id = tokenizer.convert_tokens_to_ids("yes")
    no_id = tokenizer.convert_tokens_to_ids("no")
    if yes_id is None or no_id is None or yes_id == tokenizer.unk_token_id or no_id == tokenizer.unk_token_id:
        raise RuntimeError(f"invalid yes/no token ids: yes={yes_id} no={no_id}")

    route_map = {}
    for ep in episodes:
        for r in ep["routes"]:
            route_map[r["description"]] = r["route_id"]

    def skillrouter_scorer(query: str, descriptions: list[str]) -> list[float]:
        texts = [
            format_rerank_prompt(route_map.get(desc, ""), desc, query)
            for desc in descriptions
        ]
        tokenized = []
        for text in texts:
            ids = tokenizer(
                text,
                padding=False,
                truncation=True,
                max_length=512 - len(prefix_tokens) - len(suffix_tokens),
                return_attention_mask=False,
            )["input_ids"]
            tokenized.append(prefix_tokens + ids + suffix_tokens)

        pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
        max_len = max(len(x) for x in tokenized)
        padded, masks = [], []
        for ids in tokenized:
            n = max_len - len(ids)
            padded.append([pad_id] * n + ids)
            masks.append([0] * n + [1] * len(ids))
        input_ids = torch.tensor(padded, dtype=torch.long)
        attention_mask = torch.tensor(masks, dtype=torch.long)
        with torch.no_grad():
            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits[:, -1, :]
            scores = (logits[:, yes_id] - logits[:, no_id]).float().cpu().tolist()
        return [float(x) for x in scores]

    baseline_rows = [run_episode(ep, lexical_scorer) for ep in episodes]
    model_rows = [run_episode(ep, skillrouter_scorer) for ep in episodes]
    baseline = aggregate(baseline_rows)
    candidate = aggregate(model_rows)
    result = {
        "schema": "PROJECT_BRAIN_C3_SKILLROUTER_SPENT_SCREEN_RESULT_V1",
        "status": "SPENT_DEVELOPMENT_SCREEN_ONLY__ZERO_CAPABILITY_CREDIT",
        "model": MODEL_ID,
        "model_revision": revision,
        "episodes_source": str(EPISODES_PATH),
        "baseline": baseline,
        "skillrouter": candidate,
        "terminal_success_delta": candidate["terminal_success_rate"] - baseline["terminal_success_rate"],
        "semantic_terminal_success_delta": (
            candidate["semantic_terminal_success_rate"] - baseline["semantic_terminal_success_rate"]
        ),
        "fresh_followup_justified": bool(
            candidate["terminal_success_rate"] > baseline["terminal_success_rate"]
            and candidate["semantic_terminal_success_rate"] > baseline["semantic_terminal_success_rate"]
        ),
        "baseline_rows": baseline_rows,
        "skillrouter_rows": model_rows,
        "capability_credit_delta": 0,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if not k.endswith("_rows")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
