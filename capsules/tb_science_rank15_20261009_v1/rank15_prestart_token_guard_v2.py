"""One-use prestart token-budget guard for TB-Science rank15 V2.

This script is outside the benchmark runtime closure. It may read the exact
digest-pinned task only after a fresh rank15 public lease is active. It never starts a
Harbor trial. It reconstructs the exact first-cycle planner prompt used by the
merged manifest-summary agent, counts it with the exact local planner tokenizer,
and either proves the 16K envelope fits or emits a nonconsuming abort receipt.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

from canonical.runtime import harbor_science_agent_v2 as agent
from canonical.runtime import harbor_science_planner_v2 as planner

DATASET_TASK = "terminal-bench-science/protein-active-learning"
TASK_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
SERVER_CONTEXT_TOKENS = planner.SERVER_CONTEXT_TOKENS
RESERVED_COMPLETION_TOKENS = planner.MAX_TOOL_COMPLETION_TOKENS
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_PRESTART_TOKEN_BUDGET_GUARD_V2"


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _first_cycle_prompt(goal: str) -> tuple[str, dict, dict, list, dict, list, list, str]:
    raw_task_contract, raw_task_localization, raw_task_obligations = agent._compile_lossless_task_scope(goal)
    raw_task_prompt_summary = agent._planner_raw_task_manifest_summary(
        goal, raw_task_contract, raw_task_localization, raw_task_obligations
    )
    brain_deliverables = agent._brain_mandated_deliverables(goal)
    requirements = None
    resolved: set[str] = set()
    unresolved = [] if requirements is None else sorted(set(requirements) - resolved)
    declared_inputs, declared_outputs = agent._declared_task_paths(goal)
    if declared_inputs:
        raise RuntimeError("DECLARED_INPUTS_REQUIRE_ENVIRONMENT_PRESTART_UNAVAILABLE")
    observations: list[dict] = []
    prompt = agent.build_science_planner_prompt(
        goal=goal,
        requirements=requirements,
        unresolved=unresolved,
        raw_task_prompt_summary=raw_task_prompt_summary,
        declared_inputs=declared_inputs,
        brain_deliverables=brain_deliverables,
        observations=observations,
    )
    logical_attempt_id = agent.logical_attempt_id_for_goal(goal)
    return (
        prompt,
        raw_task_contract,
        raw_task_localization,
        raw_task_obligations,
        brain_deliverables,
        declared_inputs,
        declared_outputs,
        logical_attempt_id,
    )

def _write_outputs(result: dict) -> None:
    Path("RANK15_PRESTART_GUARD.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("guard_pass=" + ("true" if result.get("pass") else "false") + "\n")
            fh.write("input_tokens=" + str(result.get("input_tokens") or "") + "\n")
            path = str(result.get("task_path") or "")
            fh.write("task_path=" + path + "\n")


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
        "acceptance_credit_delta": 0,
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
        result["runtime_goal_sha256"] = _sha_text(goal)
        prompt, contract, localization, obligations, deliverables, declared_inputs, declared_outputs, logical_attempt_id = _first_cycle_prompt(goal)
        result["first_cycle_prompt_sha256"] = _sha_text(prompt)
        result["raw_task_contract_sha256"] = contract.get("task_contract_sha256")
        summary = agent._planner_raw_task_manifest_summary(goal, contract, localization, obligations)
        result["raw_task_prompt_manifest_sha256"] = summary.get("ordered_manifest_sha256")
        result["raw_task_obligation_count"] = len(obligations)
        result["objective_route_obligation_count"] = localization.get("objective_route_obligation_count")
        result["semantic_residual_obligation_count"] = localization.get("semantic_residual_obligation_count")
        result["brain_mandated_deliverable_count"] = len(deliverables)
        result["declared_input_count"] = len(declared_inputs)
        result["declared_output_count"] = len(declared_outputs)
        payload, request_meta = planner.build_request_payload(
            prompt,
            logical_attempt_id=logical_attempt_id,
            cycle=0,
        )
        input_tokens = planner.count_input_tokens(payload)
        result["input_tokens"] = input_tokens
        result["logical_attempt_id"] = logical_attempt_id
        result["seed"] = request_meta["seed"]
        result["request_identity_sha256"] = request_meta["request_identity_sha256"]
        result["seedless_payload_sha256"] = request_meta["seedless_payload_sha256"]
        result["payload_sha256"] = hashlib.sha256(planner._payload_bytes(payload)).hexdigest()
        result["reserved_completion_tokens"] = RESERVED_COMPLETION_TOKENS
        result["server_context_tokens"] = SERVER_CONTEXT_TOKENS
        result["context_headroom_tokens"] = SERVER_CONTEXT_TOKENS - input_tokens - RESERVED_COMPLETION_TOKENS
        result["planner_module"] = "canonical.runtime.harbor_science_planner_v2"
        result["agent_module"] = "canonical.runtime.harbor_science_agent_v2"
        if input_tokens + RESERVED_COMPLETION_TOKENS > SERVER_CONTEXT_TOKENS:
            result["status"] = "PREEXPOSURE_ABORT_NONCONSUMING__TOKEN_BUDGET_EXCEEDED"
        else:
            result["pass"] = True
            result["status"] = "PASS__RANK15_V2_EXACT_TASK_READ__CANONICAL_SEEDED_PAYLOAD_FITS_16K__TASK_NOT_STARTED"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        if str(exc) == "DECLARED_INPUTS_REQUIRE_ENVIRONMENT_PRESTART_UNAVAILABLE":
            result["status"] = "PREEXPOSURE_ABORT_NONCONSUMING__DECLARED_INPUTS_REQUIRE_ENVIRONMENT"
        else:
            result["status"] = "PREEXPOSURE_ABORT_NONCONSUMING__TOKEN_GUARD_ERROR"
    _write_outputs(result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
