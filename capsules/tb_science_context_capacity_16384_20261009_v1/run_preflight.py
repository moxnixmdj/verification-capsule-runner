#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import time

from canonical.runtime import harbor_science_planner_v1 as planner

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_CONTEXT_CAPACITY_16384_ZERO_EXPOSURE_RECEIPT_V1"
OBSERVED_RANK13_REQUEST_TOKENS = 9202
PRIOR_CONTEXT_TOKENS = 8192
CANDIDATE_CONTEXT_TOKENS = 16384
HEADROOM_TOKENS = 4096
STRICT_REQUIRED_CONTEXT_TOKENS = OBSERVED_RANK13_REQUEST_TOKENS + HEADROOM_TOKENS + 1
TARGET_MIN_INPUT_TOKENS = 9250
TARGET_MAX_INPUT_TOKENS = 9400
MAX_FILLER_UNITS = 20000
MAX_SEARCH_CALLS = 24
REQUESTED_TIMEOUT_S = 300
MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
LLAMA_CPP_COMMIT = "bec4772f6a2527d371557b5d2032641e5ff7619c"
PLANNER_GIT_BLOB_SHA = "715aee168f02cb4abff961849b2b26709eef2e64"
COMMAND_POLICY_GIT_BLOB_SHA = "a525773417291c7a4841bf35e1baff5370350d0d"

_BASE = (
    "ZERO-BENCHMARK-EXPOSURE CONTEXT-CAPACITY PREFLIGHT. "
    "This is inert synthetic control-plane text. It contains no Terminal-Bench-Science task, "
    "no hidden benchmark data, and authorizes no benchmark execution. "
    "Return exactly one harmless local proposal. Use material requirement PRECHECK. "
    "The command must be 'printf context-capacity-ready' and verify_command must be "
    "'printf context-capacity-verified'. The candidate has no dependencies.\n"
)
_FILLER = "SYNTHETIC_INERT_CONTEXT_CAPACITY_UNIT "


def _canon(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _prompt(units: int) -> str:
    if not isinstance(units, int) or isinstance(units, bool) or units < 0:
        raise ValueError("FILLER_UNITS_INVALID")
    return _BASE + (_FILLER * units)


def _input_tokens(prompt: str) -> int:
    return planner.count_input_tokens(planner._request_payload(prompt))


def select_prompt():
    calls = 0
    lo, hi = 0, MAX_FILLER_UNITS
    hi_tokens = _input_tokens(_prompt(hi))
    calls += 1
    if hi_tokens < TARGET_MIN_INPUT_TOKENS:
        raise RuntimeError("TARGET_UNREACHABLE")
    best = None
    while lo <= hi and calls < MAX_SEARCH_CALLS:
        mid = (lo + hi) // 2
        prompt = _prompt(mid)
        tokens = _input_tokens(prompt)
        calls += 1
        if tokens >= TARGET_MIN_INPUT_TOKENS:
            best = (prompt, tokens, mid)
            hi = mid - 1
        else:
            lo = mid + 1
    if best is None:
        raise RuntimeError("PROMPT_SELECTION_FAILED")
    prompt, tokens, units = best
    if tokens > TARGET_MAX_INPUT_TOKENS:
        raise RuntimeError(f"PROMPT_SELECTION_OVERSHOT:{tokens}>{TARGET_MAX_INPUT_TOKENS}")
    return prompt, tokens, units, calls


def _validate_proposal(text: str):
    proposal = planner.normalize_proposal_object(planner.extract_json_object(text))
    if proposal.get("material_requirements") != ["PRECHECK"]:
        raise RuntimeError("MATERIAL_REQUIREMENTS_MISMATCH")
    candidates = proposal.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise RuntimeError("EXACTLY_ONE_CANDIDATE_REQUIRED")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise RuntimeError("CANDIDATE_OBJECT_REQUIRED")
    if candidate.get("covers") != ["PRECHECK"]:
        raise RuntimeError("CANDIDATE_COVERAGE_MISMATCH")
    if candidate.get("command") != "printf context-capacity-ready":
        raise RuntimeError("CANDIDATE_COMMAND_MISMATCH")
    if candidate.get("verify_command") != "printf context-capacity-verified":
        raise RuntimeError("CANDIDATE_VERIFY_COMMAND_MISMATCH")
    depends = candidate.get("depends_on")
    if depends not in (None, []):
        raise RuntimeError("CANDIDATE_DEPENDENCY_MISMATCH")
    return proposal


def main() -> int:
    prompt, selected_tokens, filler_units, selection_calls = select_prompt()
    if selected_tokens <= OBSERVED_RANK13_REQUEST_TOKENS:
        raise RuntimeError("PROBE_NOT_STRICTLY_ABOVE_RANK13_REQUEST")
    if CANDIDATE_CONTEXT_TOKENS < STRICT_REQUIRED_CONTEXT_TOKENS:
        raise RuntimeError("CANDIDATE_CONTEXT_LACKS_REQUIRED_HEADROOM")

    expected_timeout = planner.effective_timeout_s(selected_tokens, REQUESTED_TIMEOUT_S)
    started = time.monotonic()
    out = planner.plan(prompt, timeout_s=REQUESTED_TIMEOUT_S)
    wall_s = round(time.monotonic() - started, 3)

    if out.get("input_tokens") != selected_tokens:
        raise RuntimeError(
            f"INPUT_TOKEN_COUNT_CHANGED:{selected_tokens}!={out.get('input_tokens')}"
        )
    if out.get("effective_timeout_s") != expected_timeout:
        raise RuntimeError(
            f"EFFECTIVE_TIMEOUT_MISMATCH:{expected_timeout}!={out.get('effective_timeout_s')}"
        )
    proposal = _validate_proposal(str(out.get("text") or ""))

    core = {
        "schema": SCHEMA,
        "status": "PASS__EXACT_ROUTE_16384_CONTEXT__ZERO_EXPOSURE__SYNTHETIC_REQUEST_ABOVE_RANK13_CLASS_COMPLETED",
        "pass": True,
        "live_probe_pass": True,
        "benchmark_exposure_count": 0,
        "benchmark_trials_executed": 0,
        "harbor_execution": False,
        "rank14_task_started": False,
        "incremental_spend_usd": 0,
        "observed_rank13_request_tokens": OBSERVED_RANK13_REQUEST_TOKENS,
        "prior_context_tokens": PRIOR_CONTEXT_TOKENS,
        "candidate_context_tokens": CANDIDATE_CONTEXT_TOKENS,
        "headroom_tokens": HEADROOM_TOKENS,
        "strict_required_context_tokens": STRICT_REQUIRED_CONTEXT_TOKENS,
        "selected_input_tokens": selected_tokens,
        "observed_probe_tokens": out.get("input_tokens"),
        "filler_units": filler_units,
        "selection_token_count_calls": selection_calls,
        "requested_timeout_s": REQUESTED_TIMEOUT_S,
        "expected_effective_timeout_s": expected_timeout,
        "observed_effective_timeout_s": out.get("effective_timeout_s"),
        "planner_duration_s": out.get("duration_s"),
        "wall_duration_s": wall_s,
        "planner_transport": out.get("transport"),
        "planner_endpoint": out.get("endpoint"),
        "token_count_endpoint": out.get("token_count_endpoint"),
        "planner_model": out.get("model"),
        "proposal_candidate_count": len(proposal.get("candidates") or []),
        "proposal_material_requirements": proposal.get("material_requirements"),
        "model_sha256": MODEL_SHA256,
        "runtime_commit": LLAMA_CPP_COMMIT,
        "llama_cpp_commit": LLAMA_CPP_COMMIT,
        "planner_git_blob_sha": PLANNER_GIT_BLOB_SHA,
        "command_policy_git_blob_sha": COMMAND_POLICY_GIT_BLOB_SHA,
        "verification_authority_mutated": False,
        "context_capacity_gate_only": True,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    receipt = dict(core)
    receipt["receipt_sha256"] = hashlib.sha256(_canon(core)).hexdigest()

    pathlib.Path("CONTEXT_CAPACITY_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pathlib.Path("CONTEXT_CAPACITY_PROPOSAL.json").write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
