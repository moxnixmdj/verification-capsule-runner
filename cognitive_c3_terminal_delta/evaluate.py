#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import time
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi
from sentence_transformers import CrossEncoder

ROOT = Path(__file__).resolve().parent.parent
ROUTER_PATH = ROOT / "cognitive_c3_filtered_probe" / "cognitive_tool_router.py"
EPISODES_PATH = Path(__file__).with_name("episodes.json")
RESULT_PATH = Path(__file__).with_name("result.json")
MODEL_ID = "cross-encoder/ettin-reranker-150m-v1"

spec = importlib.util.spec_from_file_location("c3_router", ROUTER_PATH)
router = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(router)


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
        "query": ep["query"],
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


def main() -> int:
    capsule = json.loads(EPISODES_PATH.read_text())
    episodes = capsule["episodes"]

    model_info = HfApi().model_info(MODEL_ID)
    model_revision = model_info.sha
    model = CrossEncoder(MODEL_ID)

    def ettin_scorer(query: str, descriptions: list[str]) -> list[float]:
        pairs = [(query, text) for text in descriptions]
        scores = model.predict(pairs, show_progress_bar=False)
        return [float(x) for x in scores]

    baseline_rows = [run_episode(ep, lexical_scorer) for ep in episodes]
    ettin_rows = [run_episode(ep, ettin_scorer) for ep in episodes]
    baseline = aggregate(baseline_rows)
    ettin = aggregate(ettin_rows)

    delta = ettin["terminal_success_rate"] - baseline["terminal_success_rate"]
    semantic_delta = (
        ettin["semantic_terminal_success_rate"] - baseline["semantic_terminal_success_rate"]
    )

    filter_safety = all(
        r["terminal_success"]
        for r in ettin_rows
        if r["id"] in {"provider_filter_authorized", "provider_filter_unavailable", "provider_filter_unauthorized"}
    )

    result = {
        "schema": "PROJECT_BRAIN_C3_TERMINAL_TASK_DELTA_RESULT_V1",
        "status": "MEASUREMENT_ONLY__ZERO_CAPABILITY_CREDIT",
        "episodes_source": str(EPISODES_PATH),
        "model": MODEL_ID,
        "model_revision": model_revision,
        "router_source": str(ROUTER_PATH),
        "baseline": baseline,
        "ettin": ettin,
        "terminal_success_delta": delta,
        "semantic_terminal_success_delta": semantic_delta,
        "deterministic_provider_filter_safety_pass": filter_safety,
        "promotion_probe_pass": bool(
            filter_safety
            and ettin["terminal_success_rate"] > baseline["terminal_success_rate"]
            and ettin["semantic_terminal_success_rate"] > baseline["semantic_terminal_success_rate"]
            and ettin["terminal_success_rate"] >= 0.90
        ),
        "baseline_rows": baseline_rows,
        "ettin_rows": ettin_rows,
        "capability_credit_delta": 0,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("_rows")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
