#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import HfApi
from transformers import AutoModelForSequenceClassification, AutoTokenizer


MODEL_ID = "sshalimov04/open-jev-base"
MAX_LEN = 512


def render(question: str, state: Any) -> tuple[str, str]:
    statement = "The correct answer to the following decision question is yes: " + question.strip()
    seg_a = "noul | Q: Is the following statement about the text true? | statement: " + statement
    if isinstance(state, str):
        seg_b = state
    else:
        seg_b = json.dumps(state, sort_keys=True, ensure_ascii=False)
    return seg_a, seg_b


@torch.no_grad()
def score_batch(tok, model, items: list[tuple[str, Any]], batch_size: int = 16) -> list[float]:
    device = next(model.parameters()).device
    out: list[float] = []
    for i in range(0, len(items), batch_size):
        chunk = items[i:i + batch_size]
        pairs = [render(q, s) for q, s in chunk]
        enc = tok(
            [a for a, _ in pairs],
            [b for _, b in pairs],
            truncation="only_second",
            max_length=MAX_LEN,
            padding=True,
            return_tensors="pt",
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        logits = model(**enc).logits.float().squeeze(-1)
        out.extend(torch.sigmoid(logits).cpu().tolist())
    return out


def fit_calibration(probs: list[float], gold: list[bool]) -> tuple[float, float]:
    eps = 1e-6
    raw = torch.tensor([
        math.log(min(1-eps, max(eps, p)) / (1-min(1-eps, max(eps, p))))
        for p in probs
    ], dtype=torch.float64)
    y = torch.tensor([1.0 if g else 0.0 for g in gold], dtype=torch.float64)
    scale = torch.tensor(1.0, dtype=torch.float64, requires_grad=True)
    bias = torch.tensor(0.0, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([scale, bias], lr=0.5, max_iter=100, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        z = scale * raw + bias
        loss = torch.nn.functional.binary_cross_entropy_with_logits(z, y)
        loss.backward()
        return loss

    opt.step(closure)
    return float(scale.detach()), float(bias.detach())


def calibrate(p: float, scale: float, bias: float) -> float:
    eps = 1e-6
    p = min(1-eps, max(eps, p))
    z = scale * math.log(p/(1-p)) + bias
    return 1.0 / (1.0 + math.exp(-z))


def ece(rows: list[dict[str, Any]], bins: int = 10) -> float:
    total = 0.0
    n = len(rows)
    for i in range(bins):
        lo, hi = i/bins, (i+1)/bins
        b = [r for r in rows if (lo <= r["confidence"] < hi) or (i == bins-1 and r["confidence"] == 1.0)]
        if not b:
            continue
        acc = sum(r["correct"] for r in b)/len(b)
        conf = sum(r["confidence"] for r in b)/len(b)
        total += len(b)/n * abs(acc-conf)
    return total


def verifier_gold(task_path: Path, contract_id: str, candidate_id: str) -> bool:
    proc = subprocess.run(
        [
            sys.executable,
            "cognitive_kernel_real_task/run_experiment.py",
            "--worker",
            "--task", str(task_path),
            "--contract", contract_id,
            "--candidate", candidate_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(json.loads(proc.stdout)["satisfies"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--v2", required=True, type=Path)
    p.add_argument("--task", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--confidence-gate", type=float, default=0.80)
    args = p.parse_args()

    info = HfApi().model_info(MODEL_ID)
    revision = info.sha
    print(json.dumps({"resolved_model": MODEL_ID, "revision": revision}), flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=revision)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID, revision=revision, attn_implementation="sdpa"
    ).to("cpu").eval()

    v2 = [json.loads(x) for x in args.v2.read_text(encoding="utf-8").splitlines() if x.strip()]
    v2_items = [(r["question"], r["state"]) for r in v2]
    started = time.perf_counter()
    v2_raw = score_batch(tok, model, v2_items)
    v2_ms = (time.perf_counter() - started) * 1000.0
    scale, bias = fit_calibration(v2_raw, [bool(r["gold"]) for r in v2])
    print(json.dumps({"calibration_scale": scale, "calibration_bias": bias, "v2_scoring_ms": v2_ms}), flush=True)

    task = json.loads(args.task.read_text(encoding="utf-8"))
    candidates = []
    for contract in task["contracts"]:
        for candidate in contract["candidates"]:
            state = {
                "signature": contract["signature"],
                "contract": contract["contract"],
                "candidate_implementation": candidate["code"],
            }
            question = "Does this candidate implementation satisfy the contract exactly for all valid inputs?"
            candidates.append((contract, candidate, question, state))

    started = time.perf_counter()
    raw = score_batch(tok, model, [(q, s) for _, _, q, s in candidates])
    scoring_ms = (time.perf_counter() - started) * 1000.0

    rows = []
    for (contract, candidate, _, _), p_raw in zip(candidates, raw):
        p_cal = calibrate(p_raw, scale, bias)
        gold = verifier_gold(args.task, contract["id"], candidate["id"])
        pred = p_cal >= 0.5
        conf = max(p_cal, 1-p_cal)
        rows.append({
            "contract_id": contract["id"],
            "candidate_id": candidate["id"],
            "raw_probability_yes": p_raw,
            "calibrated_probability_yes": p_cal,
            "gold": gold,
            "predicted": pred,
            "correct": pred == gold,
            "confidence": conf,
        })

    n = len(rows)
    high = [r for r in rows if r["confidence"] >= args.confidence_gate]
    result = {
        "schema": "PROJECT_BRAIN_OPEN_JEV_BASE_SPENT_TASK_DIAGNOSTIC_V1",
        "status": "DIAGNOSTIC_ONLY__SPENT_TASK__ZERO_CAPABILITY_CREDIT",
        "model_id": MODEL_ID,
        "model_revision": revision,
        "calibration_source": str(args.v2),
        "calibration_scale": scale,
        "calibration_bias": bias,
        "calibration_rows": len(v2),
        "eval_rows": n,
        "accuracy": sum(r["correct"] for r in rows)/n,
        "brier": sum((r["calibrated_probability_yes"]-(1.0 if r["gold"] else 0.0))**2 for r in rows)/n,
        "ece_10bin": ece(rows),
        "high_confidence_gate": args.confidence_gate,
        "high_confidence_coverage": len(high)/n,
        "high_confidence_accuracy": (sum(r["correct"] for r in high)/len(high) if high else None),
        "model_scoring_ms": scoring_ms,
        "mean_model_scoring_ms_per_candidate": scoring_ms/n,
        "rows": rows,
        "wrong_rows": [r for r in rows if not r["correct"]],
        "wrong_high_confidence_rows": [r for r in high if not r["correct"]],
        "capability_credit_delta": 0,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("rows","wrong_rows","wrong_high_confidence_rows")}, indent=2))
    if result["wrong_high_confidence_rows"]:
        print("WRONG_HIGH_CONFIDENCE")
        print(json.dumps(result["wrong_high_confidence_rows"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
