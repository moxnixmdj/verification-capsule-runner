"""One-use prestart all-cycle context-fit guard for TB-Science rank15 V3.

Reads the exact digest-pinned task only after a fresh public lease. It never starts
Harbor. It proves both the exact cycle-0 seeded request and a structurally maximal
later-cycle fixed state fit the 16K planner envelope before task start.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from canonical.runtime import harbor_science_agent_v3 as agent
from canonical.runtime import harbor_science_planner_v3 as planner

DATASET_TASK = "terminal-bench-science/protein-active-learning"
TASK_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
SERVER_CONTEXT_TOKENS = planner.SERVER_CONTEXT_TOKENS
RESERVED_COMPLETION_TOKENS = planner.MAX_TOOL_COMPLETION_TOKENS
MAX_INPUT_TOKENS = SERVER_CONTEXT_TOKENS - RESERVED_COMPLETION_TOKENS
# 29 variable 64-hex refs -> at most 29*63 tokenization-variance tokens,
# plus 12*16 action-id preview and 16*8 requirement-label preview variance.
STRUCTURAL_TOKEN_VARIANCE_RESERVE = 2304
SYNTHETIC_CATALOG_RECORDS = 128
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_PRESTART_ALL_CYCLE_FIT_GUARD_V3"


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compile(goal: str):
    contract, localization, obligations = agent._compile_lossless_task_scope(goal)
    summary = agent._planner_raw_task_manifest_summary(
        goal, contract, localization, obligations
    )
    deliverables = agent._brain_mandated_deliverables(goal)
    declared_inputs, declared_outputs = agent._declared_task_paths(goal)
    return (
        contract,
        localization,
        obligations,
        summary,
        deliverables,
        declared_inputs,
        declared_outputs,
    )


def _maximal_catalog() -> list[dict]:
    rows = []
    for i in range(SYNTHETIC_CATALOG_RECORDS):
        rows.append({
            "ref": hashlib.sha256(f"synthetic-evidence-{i}".encode()).hexdigest(),
            "kind": "K" * 64,
            "cycle": i % agent.MAX_CYCLES,
            "action_id": ("A" + str(i).zfill(15))[-agent.EVIDENCE_ACTION_ID_PREVIEW_CHARS:],
            "returncode": 255,
            "coverage_promoted": bool(i % 2),
        })
    return rows


def _maximal_requirements() -> list[str]:
    rows = []
    for i in range(agent.MAX_REQUIREMENTS):
        prefix = f"REQ{i:02d}."
        rows.append(prefix + ("X" * (64 - len(prefix))))
    return rows


def _fit(
    *,
    goal: str,
    requirements,
    unresolved,
    summary: dict,
    declared_inputs: list[str],
    deliverables: dict[str, str],
    catalog: list[dict],
    cycle: int,
    logical_attempt_id: str,
):
    store: dict[str, str] = {}
    prompt, pack = agent.build_fitting_science_planner_prompt(
        goal=goal,
        requirements=requirements,
        unresolved=unresolved,
        raw_task_prompt_summary=summary,
        declared_inputs=declared_inputs,
        brain_deliverables=deliverables,
        evidence_store=store,
        evidence_catalog=catalog,
        requested_refs=[],
        logical_attempt_id=logical_attempt_id,
        cycle=cycle,
    )
    payload, meta = planner.build_request_payload(
        prompt,
        logical_attempt_id=logical_attempt_id,
        cycle=cycle,
    )
    exact_tokens = planner.count_input_tokens(payload)
    if exact_tokens != pack["input_tokens"]:
        raise RuntimeError("PACKER_TOKEN_COUNT_NONDETERMINISTIC")
    return prompt, payload, meta, pack


def _write(result: dict) -> None:
    Path("RANK15_PRESTART_ALL_CYCLE_FIT_GUARD.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("guard_pass=" + ("true" if result.get("pass") else "false") + "\n")
            fh.write("task_path=" + str(result.get("task_path") or "") + "\n")


def main() -> int:
    result = {
        "schema": SCHEMA,
        "status": "PREEXPOSURE_ABORT_NONCONSUMING__GUARD_NOT_COMPLETED",
        "pass": False,
        "slot_id": DATASET_TASK + "::trial-0",
        "task_digest": TASK_DIGEST,
        "task_read": False,
        "task_started": False,
        "execution_authority_consumed": False,
        "benchmark_trials_consumed": 0,
        "terminal_credit_delta": 0,
    }
    try:
        root = Path("rank15_task_read").resolve()
        root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "harbor", "task", "download",
                DATASET_TASK + "@" + TASK_DIGEST,
                "--output-dir", str(root),
                "--overwrite",
                "--export",
            ],
            check=True,
        )
        task_path = root / "protein-active-learning"
        instruction_path = task_path / "instruction.md"
        task_toml = task_path / "task.toml"
        if not instruction_path.is_file() or not task_toml.is_file():
            raise RuntimeError("DIGEST_PINNED_TASK_EXPORT_INCOMPLETE")
        raw_instruction = instruction_path.read_text(encoding="utf-8")
        goal = raw_instruction.strip()
        if not goal:
            raise RuntimeError("DIGEST_PINNED_TASK_INSTRUCTION_EMPTY")
        result["task_read"] = True
        result["task_path"] = str(task_path)
        result["instruction_sha256"] = _sha_text(raw_instruction)

        (
            contract,
            localization,
            obligations,
            summary,
            deliverables,
            declared_inputs,
            declared_outputs,
        ) = _compile(goal)
        if declared_inputs:
            raise RuntimeError("DECLARED_INPUTS_REQUIRE_ENVIRONMENT_PRESTART_UNAVAILABLE")

        logical_attempt_id = agent.logical_attempt_id_for_goal(goal)

        p0, payload0, meta0, pack0 = _fit(
            goal=goal,
            requirements=None,
            unresolved=[],
            summary=summary,
            declared_inputs=declared_inputs,
            deliverables=deliverables,
            catalog=[],
            cycle=0,
            logical_attempt_id=logical_attempt_id,
        )

        worst_requirements = _maximal_requirements()
        pw, payloadw, metaw, packw = _fit(
            goal=goal,
            requirements=worst_requirements,
            unresolved=worst_requirements,
            summary=summary,
            declared_inputs=declared_inputs,
            deliverables=deliverables,
            catalog=_maximal_catalog(),
            cycle=agent.MAX_CYCLES - 1,
            logical_attempt_id=logical_attempt_id,
        )

        conservative_worst = (
            int(packw["input_tokens"]) + STRUCTURAL_TOKEN_VARIANCE_RESERVE
        )
        if conservative_worst > MAX_INPUT_TOKENS:
            raise RuntimeError(
                "ALL_CYCLE_FIXED_STATE_RESERVE_EXCEEDED:"
                f"{packw['input_tokens']}+{STRUCTURAL_TOKEN_VARIANCE_RESERVE}>"
                f"{MAX_INPUT_TOKENS}"
            )

        result.update({
            "pass": True,
            "status": "PASS__EXACT_RANK15_CYCLE0_AND_CONSERVATIVE_ALL_CYCLE_FIXED_STATE_FIT__TASK_NOT_STARTED",
            "logical_attempt_id": logical_attempt_id,
            "raw_task_contract_sha256": contract.get("task_contract_sha256"),
            "raw_task_prompt_manifest_sha256": summary.get("ordered_manifest_sha256"),
            "raw_task_obligation_count": len(obligations),
            "objective_route_obligation_count": localization.get("objective_route_obligation_count"),
            "semantic_residual_obligation_count": localization.get("semantic_residual_obligation_count"),
            "brain_mandated_deliverable_count": len(deliverables),
            "declared_output_count": len(declared_outputs),
            "cycle0_input_tokens": pack0["input_tokens"],
            "cycle0_context_headroom_tokens": MAX_INPUT_TOKENS - pack0["input_tokens"],
            "cycle0_prompt_sha256": _sha_text(p0),
            "cycle0_payload_sha256": hashlib.sha256(planner._payload_bytes(payload0)).hexdigest(),
            "cycle0_seed": meta0["seed"],
            "maximal_fixed_state_input_tokens_observed": packw["input_tokens"],
            "structural_token_variance_reserve": STRUCTURAL_TOKEN_VARIANCE_RESERVE,
            "conservative_maximal_fixed_state_tokens": conservative_worst,
            "all_cycle_reserved_headroom_tokens": MAX_INPUT_TOKENS - conservative_worst,
            "maximal_fixed_state_prompt_sha256": _sha_text(pw),
            "maximal_fixed_state_payload_sha256": hashlib.sha256(planner._payload_bytes(payloadw)).hexdigest(),
            "maximal_fixed_state_seed": metaw["seed"],
            "server_context_tokens": SERVER_CONTEXT_TOKENS,
            "reserved_completion_tokens": RESERVED_COMPLETION_TOKENS,
            "maximum_input_tokens": MAX_INPUT_TOKENS,
            "synthetic_catalog_records": SYNTHETIC_CATALOG_RECORDS,
            "maximum_requirements": agent.MAX_REQUIREMENTS,
            "requirement_aliases": "R01..R16",
            "dynamic_requested_evidence_policy": "EXACT_TOKEN_PACK_THEN_DEFER",
            "task_started": False,
            "execution_authority_consumed": False,
            "benchmark_trials_consumed": 0,
        })
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["status"] = "PREEXPOSURE_ABORT_NONCONSUMING__ALL_CYCLE_FIT_GUARD_ERROR"
    _write(result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
