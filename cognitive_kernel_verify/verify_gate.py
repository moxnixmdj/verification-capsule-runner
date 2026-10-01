#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_kernel(path: Path):
    spec = importlib.util.spec_from_file_location("cognitive_decision_kernel", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True, type=Path)
    p.add_argument("--kernel", required=True, type=Path)
    p.add_argument("--endpoint", required=True)
    p.add_argument("--model", default="jev-latest")
    p.add_argument("--threshold", type=float, default=0.80)
    p.add_argument("--min-coverage", type=float, default=0.30)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    kernel = load_kernel(args.kernel)
    cases = [
        json.loads(line)
        for line in args.cases.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    rows = []
    for case in cases:
        result = kernel.decide(
            endpoint=args.endpoint,
            model=args.model,
            state=case["state"],
            question=case["question"],
            threshold=args.threshold,
        )
        admitted = result.status == "ADMIT"
        correct = None if not admitted else (result.decision == case["gold"])
        rows.append({
            "id": case["id"],
            "domain": case["domain"],
            "primitive": case["primitive"],
            "gold": case["gold"],
            "status": result.status,
            "decision": result.decision,
            "probability_yes": result.probability_yes,
            "confidence": result.confidence,
            "latency_ms": result.latency_ms,
            "admitted_correct": correct,
        })

    admitted = [r for r in rows if r["status"] == "ADMIT"]
    wrong = [r for r in admitted if r["admitted_correct"] is False]
    coverage = len(admitted) / len(rows)

    output = {
        "schema": "PROJECT_BRAIN_COGNITIVE_DECISION_KERNEL_GATE_VERIFY_V1",
        "status": (
            "PASS" if not wrong and coverage >= args.min_coverage
            else "FAIL"
        ),
        "threshold": args.threshold,
        "cases": len(rows),
        "admitted": len(admitted),
        "escalated": len(rows) - len(admitted),
        "coverage": coverage,
        "wrong_admissions": len(wrong),
        "min_coverage_required": args.min_coverage,
        "rows": rows,
        "capability_credit_delta": 0,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in output.items() if k != "rows"}, indent=2))

    if wrong:
        print("WRONG_ADMISSIONS")
        print(json.dumps(wrong, indent=2))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
