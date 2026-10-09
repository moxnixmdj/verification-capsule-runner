"""One-use prestart token-budget guard for TB-Science rank14.

This script is intentionally outside the benchmark runtime closure. It may read the
exact digest-pinned task only after the public execution lease is active. It never
starts a Harbor trial. It either proves the exact first-cycle planner request fits
the verified 16K context envelope or emits a nonconsuming abort receipt.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

from canonical.runtime import harbor_science_agent_v1 as agent
from canonical.runtime import harbor_science_planner_v1 as planner

DATASET_TASK = "terminal-bench-science/inverse-lithography"
TASK_DIGEST = "sha256:8c4da4b5b3a00283335e83dda92584aaf9293ff773bc43f2bf95eb0e2c0f8530"
SERVER_CONTEXT_TOKENS = 16384
RESERVED_COMPLETION_TOKENS = 4096
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK14_PRESTART_TOKEN_BUDGET_GUARD_V1"


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _first_cycle_prompt(goal: str) -> tuple[str, dict, dict, list, dict, list, list]:
    raw_task_contract, raw_task_localization, raw_task_obligations = agent._compile_lossless_task_scope(goal)
    brain_deliverables = agent._brain_mandated_deliverables(goal)
    requirements = None
    resolved: set[str] = set()
    unresolved = [] if requirements is None else sorted(set(requirements) - resolved)
    declared_inputs, declared_outputs = agent._declared_task_paths(goal)
    if declared_inputs:
        raise RuntimeError("DECLARED_INPUTS_REQUIRE_ENVIRONMENT_PRESTART_UNAVAILABLE")
    observations: list[dict] = []
    prompt = (
        "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
        "Return one structured proposal object only. Project Brain owns action selection, command policy, verification, "
        "requirement-state updates, and finish authority. No network acquisition, package installation, "
        "git fetch/clone/pull, secrets, or host escape. "
        "On the first cycle provide material_requirements (1-16 stable short IDs). "
        "Provide 1-4 candidate actions as {action_id,covers,depends_on?,timeout_sec?,verify_timeout_sec?,command,verify_command}. "
        "Use depends_on only for true within-proposal sequencing. covers must name only frozen material_requirements. "
        "Brain may execute multiple nonredundant candidates from one proposal, but promotes each claimed effect only "
        "after its independent verify_command succeeds. Brain alone decides completion after "
        "independent verification resolves every frozen material requirement. finish_summary is optional "
        "descriptive metadata only and never execution or finish authority. "
        f"Goal: {goal}\nFrozen requirements: {requirements!r}\nUnresolved: {unresolved!r}\n"
        "Brain lossless raw-task obligation quotient (non-droppable; exact text is the Goal span above): "
        + json.dumps(raw_task_obligations, sort_keys=True)
        + "\nEvery raw obligation remains acceptance-pending until exact candidate-bound independent acceptance exists. "
        "Use Goal[span[0]:span[1]] as the authoritative obligation text; IDs and covers are routing metadata only.\n"
        "Brain-declared authoritative local inputs: "
        + json.dumps(declared_inputs, sort_keys=True)
        + "\nBrain-mandated explicit deliverables (requirement ID -> path): "
        + json.dumps(brain_deliverables, sort_keys=True)
        + "\nThe BRAIN_DECLARED_INPUT_SNAPSHOT observations below are exact local task-source reads. "
        "Use those bytes instead of guessing plant parameters, interfaces, scenarios, or other declared source facts. "
        "These Brain-mandated requirement IDs are part of the frozen contract and may not be omitted. "
        "A candidate claiming one of them must actually create that exact nonempty file; Brain validates it independently.\n"
        "Recent observations: " + json.dumps(observations[-8:], sort_keys=True)[:30000]
    )
    return prompt, raw_task_contract, raw_task_localization, raw_task_obligations, brain_deliverables, declared_inputs, declared_outputs


def _write_outputs(result: dict) -> None:
    Path("RANK14_PRESTART_GUARD.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
        root = Path("rank14_task_read").resolve()
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
        task_path = root / "inverse-lithography"
        instruction_path = task_path / "instruction.md"
        task_toml = task_path / "task.toml"
        if not instruction_path.is_file() or not task_toml.is_file():
            raise RuntimeError("DIGEST_PINNED_TASK_EXPORT_INCOMPLETE")
        goal = instruction_path.read_text(encoding="utf-8")
        result["task_read"] = True
        result["task_path"] = str(task_path)
        result["instruction_sha256"] = _sha_text(goal)
        prompt, contract, localization, obligations, deliverables, declared_inputs, declared_outputs = _first_cycle_prompt(goal)
        result["first_cycle_prompt_sha256"] = _sha_text(prompt)
        result["raw_task_contract_sha256"] = contract.get("task_contract_sha256")
        result["raw_task_obligation_count"] = len(obligations)
        result["objective_route_obligation_count"] = localization.get("objective_route_obligation_count")
        result["semantic_residual_obligation_count"] = localization.get("semantic_residual_obligation_count")
        result["brain_mandated_deliverable_count"] = len(deliverables)
        result["declared_input_count"] = len(declared_inputs)
        result["declared_output_count"] = len(declared_outputs)
        payload = planner._request_payload(prompt)
        input_tokens = planner.count_input_tokens(payload)
        result["input_tokens"] = input_tokens
        result["reserved_completion_tokens"] = RESERVED_COMPLETION_TOKENS
        result["server_context_tokens"] = SERVER_CONTEXT_TOKENS
        result["context_headroom_tokens"] = SERVER_CONTEXT_TOKENS - input_tokens - RESERVED_COMPLETION_TOKENS
        result["planner_blob_expected"] = "58964dc8d6b5eed5c202081cd800035c791eeb1d"
        if input_tokens + RESERVED_COMPLETION_TOKENS > SERVER_CONTEXT_TOKENS:
            result["status"] = "PREEXPOSURE_ABORT_NONCONSUMING__TOKEN_BUDGET_EXCEEDED"
        else:
            result["pass"] = True
            result["status"] = "PASS__RANK14_EXACT_TASK_READ__TOKEN_BUDGET_FITS_16K__TASK_NOT_STARTED"
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
