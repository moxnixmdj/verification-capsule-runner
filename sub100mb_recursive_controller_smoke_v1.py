#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

MODEL_BYTES = 93_511_232
BUDGET_BYTES_EXCLUSIVE = 100_000_000
MODEL_SHA256 = "61c69fc5ce91982e26c625d43be5c3c7f0f774da22f4fa4e45c37a80a22ddad4"

TASKS = [
    {
        "id": "plate_one_hole",
        "observations": (
            "Front view: rectangle 80 mm wide and 50 mm high. "
            "Side view: constant depth 12 mm. "
            "A through hole diameter 10 mm is centered at x=40 mm, y=25 mm."
        ),
        "expected": {
            "units": "mm",
            "geometry": {"kind": "extruded", "profile": "rectangle", "width": 80, "height": 50, "thickness": 12},
            "holes": [{"x": 40, "y": 25, "diameter": 10, "hole_type": "through"}],
        },
    },
    {
        "id": "plate_two_holes",
        "observations": (
            "Front view: rectangular plate 100 mm by 60 mm. "
            "Side view: thickness 8 mm. Two identical through holes diameter 6 mm "
            "lie on y=30 mm at x=20 mm and x=80 mm."
        ),
        "expected": {
            "units": "mm",
            "geometry": {"kind": "extruded", "profile": "rectangle", "width": 100, "height": 60, "thickness": 8},
            "holes": [
                {"x": 20, "y": 30, "diameter": 6, "hole_type": "through"},
                {"x": 80, "y": 30, "diameter": 6, "hole_type": "through"},
            ],
        },
    },
    {
        "id": "counterbore_plate",
        "observations": (
            "Front view: rectangular plate 90 mm wide by 40 mm high. "
            "Thickness is 10 mm. At x=45 mm,y=20 mm there is a through bore diameter 8 mm "
            "with a counterbore diameter 16 mm and counterbore depth 3 mm."
        ),
        "expected": {
            "units": "mm",
            "geometry": {"kind": "extruded", "profile": "rectangle", "width": 90, "height": 40, "thickness": 10},
            "holes": [{
                "x": 45, "y": 20, "diameter": 8, "hole_type": "counterbore",
                "counterbore_diameter": 16, "counterbore_depth": 3
            }],
        },
    },
    {
        "id": "stepped_shaft",
        "observations": (
            "A rotationally symmetric stepped shaft is shown about the z axis. "
            "From z=0 to z=30 mm the outside diameter is 20 mm. "
            "From z=30 to z=50 mm the outside diameter is 30 mm. There is no bore."
        ),
        "expected": {
            "units": "mm",
            "geometry": {
                "kind": "revolved",
                "segments": [
                    {"z_start": 0, "z_end": 30, "outer_diameter": 20, "inner_diameter": 0},
                    {"z_start": 30, "z_end": 50, "outer_diameter": 30, "inner_diameter": 0},
                ],
            },
            "holes": [],
        },
    },
    {
        "id": "l_bracket",
        "observations": (
            "An L bracket consists of two rectangular additive solids in one coordinate frame. "
            "Base: min corner (0,0,0), size dx=80,dy=40,dz=8. "
            "Vertical web: min corner (0,0,8), size dx=8,dy=40,dz=42. "
            "No holes or cuts."
        ),
        "expected": {
            "units": "mm",
            "geometry": {
                "kind": "multibody",
                "bodies": [
                    {"shape": "box", "operation": "add", "x": 0, "y": 0, "z": 0, "dx": 80, "dy": 40, "dz": 8},
                    {"shape": "box", "operation": "add", "x": 0, "y": 0, "z": 8, "dx": 8, "dy": 40, "dz": 42},
                ],
            },
            "holes": [],
        },
    },
    {
        "id": "triangular_prism",
        "observations": (
            "A prism has a triangular XY profile with ordered vertices (0,0), (60,0), (0,40) mm "
            "and is extruded 12 mm along z. No holes."
        ),
        "expected": {
            "units": "mm",
            "geometry": {
                "kind": "extruded",
                "profile": "polygon",
                "profile_points": [[0, 0], [60, 0], [0, 40]],
                "thickness": 12,
            },
            "holes": [],
        },
    },
    {
        "id": "unsupported_envelope",
        "observations": (
            "The drawing shows a freeform cast surface that this schema cannot represent exactly. "
            "The readable overall envelope is width 120 mm, height 80 mm, depth 30 mm. "
            "Do not invent primitive geometry."
        ),
        "expected": {
            "units": "mm",
            "geometry": {
                "kind": "unsupported",
                "envelope_width": 120,
                "envelope_height": 80,
                "envelope_depth": 30,
            },
            "holes": [],
        },
    },
    {
        "id": "inch_plate",
        "observations": (
            "Units are inches. Rectangular plate width 4 in, height 2 in, thickness 0.25 in. "
            "One through hole diameter 0.5 in is centered at x=2 in,y=1 in."
        ),
        "expected": {
            "units": "in",
            "geometry": {"kind": "extruded", "profile": "rectangle", "width": 4, "height": 2, "thickness": 0.25},
            "holes": [{"x": 2, "y": 1, "diameter": 0.5, "hole_type": "through"}],
        },
    },
]

SCHEMA = """PartSpecLite JSON rules:
- top-level keys: units, geometry, holes.
- units is "mm" or "in".
- extruded rectangle geometry:
  {"kind":"extruded","profile":"rectangle","width":number,"height":number,"thickness":number}
- extruded polygon geometry:
  {"kind":"extruded","profile":"polygon","profile_points":[[x,y],...],"thickness":number}
- revolved geometry:
  {"kind":"revolved","segments":[{"z_start":number,"z_end":number,"outer_diameter":number,"inner_diameter":number},...]}
- multibody geometry:
  {"kind":"multibody","bodies":[{"shape":"box","operation":"add","x":number,"y":number,"z":number,"dx":number,"dy":number,"dz":number},...]}
- unsupported geometry:
  {"kind":"unsupported","envelope_width":number,"envelope_height":number,"envelope_depth":number}
- hole:
  {"x":number,"y":number,"diameter":number,"hole_type":"through"}
  or for counterbore add counterbore_diameter and counterbore_depth and set hole_type="counterbore".
Return JSON only. Do not add commentary or keys not required by the observations.
"""

def call(endpoint: str, prompt: str, temperature: float, seed: int, max_tokens: int = 320) -> str:
    body = json.dumps({
        "model": "sub100mb-controller",
        "messages": [
            {"role": "system", "content": "You are a precise typed transformation engine. Follow the requested schema exactly."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "seed": seed,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        obj = json.loads(r.read())
    return obj["choices"][0]["message"]["content"]

def extract_json(text: str) -> Any:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("NO_JSON_OBJECT")
    return json.loads(m.group(0))

def same_number(a: Any, b: Any) -> bool:
    return isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool) and abs(float(a) - float(b)) <= 1e-9

def validate(actual: Any, expected: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}:expected_object"]
        extra = sorted(set(actual) - set(expected))
        missing = sorted(set(expected) - set(actual))
        if extra:
            errors.append(f"{path}:extra_keys={extra}")
        if missing:
            errors.append(f"{path}:missing_keys={missing}")
        for k in expected:
            if k in actual:
                errors.extend(validate(actual[k], expected[k], f"{path}.{k}"))
        return errors
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}:expected_list"]
        if len(actual) != len(expected):
            errors.append(f"{path}:length={len(actual)} expected={len(expected)}")
            return errors
        for i, exp in enumerate(expected):
            errors.extend(validate(actual[i], exp, f"{path}[{i}]"))
        return errors
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not same_number(actual, expected):
            errors.append(f"{path}:value={actual!r} expected={expected!r}")
        return errors
    if actual != expected:
        errors.append(f"{path}:value={actual!r} expected={expected!r}")
    return errors

def evaluate_text(text: str, expected: dict[str, Any]) -> tuple[bool, list[str], Any]:
    try:
        parsed = extract_json(text)
    except Exception as exc:
        return False, [f"parse:{exc}"], None
    errors = validate(parsed, expected)
    return not errors, errors, parsed

def direct_prompt(task: dict[str, Any]) -> str:
    return (
        "Convert the observations into a compact PartSpecLite JSON object with top-level keys "
        "units, geometry, holes. Use literal dimensions exactly. Return JSON only.\n\n"
        f"Observations:\n{task['observations']}"
    )

def schema_prompt(task: dict[str, Any]) -> str:
    return f"{SCHEMA}\nObservations:\n{task['observations']}"

def repair_prompt(task: dict[str, Any], previous: str, errors: list[str]) -> str:
    err = "\n".join("- " + e for e in errors[:20])
    return (
        f"{SCHEMA}\nObservations:\n{task['observations']}\n\n"
        "The previous candidate failed deterministic validation. Repair it. "
        "Do not merely explain the errors. Return a complete corrected JSON object only.\n"
        f"Validation errors:\n{err}\nPrevious candidate:\n{previous}"
    )

def wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p = successes / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2*n)) / den
    half = z * math.sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return [max(0.0, center-half), min(1.0, center+half)]

def summarize(name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    proposals = [p for r in records for p in r["proposals"]]
    proposal_success = sum(1 for p in proposals if p["passed"])
    task_success = sum(1 for r in records if r["passed"])
    return {
        "condition": name,
        "task_count": len(records),
        "tasks_solved": task_success,
        "task_success_rate": task_success / len(records),
        "proposal_count": len(proposals),
        "passing_proposals": proposal_success,
        "proposal_success_rate_p_hat": proposal_success / len(proposals) if proposals else 0.0,
        "proposal_success_wilson95": wilson(proposal_success, len(proposals)),
        "mean_proposals_per_task": len(proposals) / len(records),
    }

def run(endpoint: str) -> dict[str, Any]:
    results: dict[str, list[dict[str, Any]]] = {k: [] for k in ["direct", "schema", "feedback", "search4"]}

    for ti, task in enumerate(TASKS):
        # Direct single shot.
        text = call(endpoint, direct_prompt(task), 0.0, 1000 + ti)
        passed, errors, parsed = evaluate_text(text, task["expected"])
        results["direct"].append({"task_id": task["id"], "passed": passed, "proposals": [{
            "attempt": 1, "passed": passed, "errors": errors, "output": text, "parsed": parsed
        }]})

        # Schema-constrained single shot.
        text = call(endpoint, schema_prompt(task), 0.0, 2000 + ti)
        passed, errors, parsed = evaluate_text(text, task["expected"])
        results["schema"].append({"task_id": task["id"], "passed": passed, "proposals": [{
            "attempt": 1, "passed": passed, "errors": errors, "output": text, "parsed": parsed
        }]})

        # Up to four recursive proposals, where only deterministic validator errors return.
        proposals = []
        prompt = schema_prompt(task)
        previous = ""
        passed = False
        errors: list[str] = []
        for attempt in range(1, 5):
            text = call(endpoint, prompt, 0.0, 3000 + ti * 10 + attempt)
            passed, errors, parsed = evaluate_text(text, task["expected"])
            proposals.append({"attempt": attempt, "passed": passed, "errors": errors, "output": text, "parsed": parsed})
            if passed:
                break
            previous = text
            prompt = repair_prompt(task, previous, errors)
        results["feedback"].append({"task_id": task["id"], "passed": passed, "proposals": proposals})

        # Four independent candidates, deterministic selector chooses any exact pass.
        proposals = []
        for attempt, temp in enumerate([0.0, 0.2, 0.5, 0.8], start=1):
            text = call(endpoint, schema_prompt(task), temp, 4000 + ti * 10 + attempt)
            p, e, parsed = evaluate_text(text, task["expected"])
            proposals.append({"attempt": attempt, "temperature": temp, "passed": p, "errors": e, "output": text, "parsed": parsed})
        results["search4"].append({"task_id": task["id"], "passed": any(p["passed"] for p in proposals), "proposals": proposals})

    summaries = {name: summarize(name, recs) for name, recs in results.items()}
    direct_p = summaries["direct"]["proposal_success_rate_p_hat"]
    feedback_task = summaries["feedback"]["task_success_rate"]
    search_task = summaries["search4"]["task_success_rate"]

    return {
        "schema": "PROJECT_BRAIN_SUB100MB_RECURSIVE_CONTROLLER_SMOKE_RESULT_V1",
        "status": "EMPIRICAL_RESEARCH_RESULT__ZERO_TERMINAL_CREDIT",
        "model": {
            "artifact": "SmolLM2-135M-Instruct-Q3_K_M.gguf",
            "sha256": MODEL_SHA256,
            "learned_bytes": MODEL_BYTES,
            "strict_budget_bytes_exclusive": BUDGET_BYTES_EXCLUSIVE,
            "remaining_bytes": BUDGET_BYTES_EXCLUSIVE - MODEL_BYTES,
        },
        "population": {
            "kind": "SYNTHETIC_NONTERMINAL_PARTSPECLITE_TEXT_SURROGATES",
            "task_count": len(TASKS),
            "fresh_terminal_reality_consumed": 0,
            "claim_scope": "CONTROLLER_MECHANISM_SMOKE_ONLY",
        },
        "summaries": summaries,
        "architecture_signal": {
            "direct_single_shot_p": direct_p,
            "feedback_task_success_rate": feedback_task,
            "search4_task_success_rate": search_task,
            "feedback_improves_task_success_over_direct": feedback_task > summaries["direct"]["task_success_rate"],
            "search_improves_task_success_over_direct": search_task > summaries["direct"]["task_success_rate"],
        },
        "records": results,
        "hard_nonclaims": [
            "NO_FRONTIER_CAPABILITY_CLAIM",
            "NO_IMAGE_PERCEPTION_CLAIM",
            "NO_OPUS55_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
            "NO_OPEN_WORLD_GENERALIZATION_CLAIM",
            "NO_CLAIM_SYNTHETIC_TASKS_ESTIMATE_TERMINAL_SUCCESS_PROBABILITY",
        ],
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8080")
    ap.add_argument("--out", default="sub100mb_recursive_controller_smoke_result_v1.json")
    args = ap.parse_args()
    result = run(args.endpoint)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({"summaries": result["summaries"], "architecture_signal": result["architecture_signal"]}, indent=2))

if __name__ == "__main__":
    main()
