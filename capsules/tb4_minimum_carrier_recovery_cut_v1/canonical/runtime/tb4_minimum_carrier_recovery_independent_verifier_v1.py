"""Independent verifier for TB4 minimum carrier recovery cut v1.

Re-derives resource rows directly from task.toml at the exact public source commit.
It intentionally does NOT prove frozen benchmark task-identity equivalence, carrier existence,
protocol equivalence, execution authority, or capability credit.
"""
from __future__ import annotations
import hashlib, json, math, os, subprocess, tomllib
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json"
COMPAT = ROOT / "canonical/verification/TB4_FULL_CARRIER_COMPATIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
MANIFEST = ROOT / "canonical/governance/TB4_ATTAINABILITY_EVIDENCE_MANIFEST_V1.json"
ATTAIN = ROOT / "canonical/verification/TB4_ATTAINABILITY_CUT_VERDICT_20261002_V1.json"
SCHEMA = "PROJECT_BRAIN_TB4_MINIMUM_CARRIER_RECOVERY_CUT_INDEPENDENT_VERDICT_V1"

def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def norm_num(v: Any) -> int | float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError("invalid numeric resource")
    return int(v) if float(v).is_integer() else float(v)

def fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "resource_metadata_independently_reproduced": False,
        "task_identity_binding": False,
        "concrete_carrier_bound": False,
        "protocol_equivalence_bound": False,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "fresh_acceptance_cases_consumed": 0,
    }

def derive_rows(source_root: Path, host: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str], int]:
    tasks_root = source_root / "tasks"
    tomls = sorted(tasks_root.glob("*/task.toml"))
    rows: list[dict[str, Any]] = []
    gpu_tasks: list[str] = []
    exceeds: list[dict[str, Any]] = []
    for p in tomls:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        env = data.get("environment") or {}
        cpus = norm_num(float(env.get("cpus") or 0))
        memory_mb = norm_num(int(env.get("memory_mb") or 0))
        storage_mb = norm_num(int(env.get("storage_mb") or 0))
        gpus = norm_num(int(env.get("gpus") or 0))
        name = (data.get("task") or {}).get("name") or p.parent.name
        row = {"task": name, "cpus": cpus, "memory_mb": memory_mb, "storage_mb": storage_mb, "gpus": gpus}
        rows.append(row)
        if gpus > 0:
            gpu_tasks.append(name)
        if cpus > host["cpus"] or memory_mb > host["memory_mb"] or storage_mb > host["free_storage_mb"]:
            exceeds.append(row)
    return exceeds, gpu_tasks, len(tomls)

def evaluate(
    spec: Mapping[str, Any],
    compat: Mapping[str, Any],
    manifest: Mapping[str, Any],
    attain: Mapping[str, Any],
    source_root: Path,
    source_shas: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []

    auth = spec.get("authority") or {}
    expected = {
        "carrier_compatibility_verification": source_shas["compat"],
        "attainability_manifest": source_shas["manifest"],
        "attainability_verdict": source_shas["attain"],
    }
    for key, sha in expected.items():
        row = auth.get(key)
        if not isinstance(row, Mapping) or row.get("git_blob_sha") != sha:
            errors.append("AUTHORITY_BLOB_MISMATCH:" + key)

    dataset = compat.get("dataset") or {}
    source_commit = dataset.get("commit")
    try:
        actual_commit = subprocess.check_output(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        actual_commit = None
        errors.append("SOURCE_GIT_HEAD_UNREADABLE")
    if actual_commit != source_commit:
        errors.append("SOURCE_COMMIT_MISMATCH")
    if dataset.get("task_count") != 66:
        errors.append("SOURCE_TASK_COUNT_DECLARATION_MISMATCH")

    host = compat.get("observed_runner") or {}
    required_host_keys = ("cpus", "memory_mb", "free_storage_mb", "docker", "docker_compose")
    if any(k not in host for k in required_host_keys):
        errors.append("OBSERVED_RUNNER_INCOMPLETE")
        return fail(errors)

    try:
        exceeds, gpu_tasks, task_count = derive_rows(source_root, host)
    except Exception as exc:
        errors.append("RESOURCE_METADATA_REPRODUCTION_FAILED:" + type(exc).__name__)
        return fail(errors)

    if task_count != 66:
        errors.append("REPRODUCED_TASK_COUNT_NOT_66")
    if len(exceeds) != 12:
        errors.append("REPRODUCED_RESOURCE_EXCEED_COUNT_NOT_12")
    if len(gpu_tasks) != 3:
        errors.append("REPRODUCED_GPU_TASK_COUNT_NOT_3")
    if sorted(gpu_tasks) != sorted(compat.get("exact_population_requirements", {}).get("gpu_tasks", [])):
        errors.append("GPU_TASK_SET_MISMATCH")

    cand_rows = spec.get("resource_exceed_tasks")
    if not isinstance(cand_rows, list):
        errors.append("CANDIDATE_RESOURCE_ROWS_INVALID")
        cand_rows = []
    def canon(rows: list[Mapping[str, Any]]) -> list[tuple[Any, ...]]:
        return sorted(
            (r.get("task"), norm_num(r.get("cpus")), norm_num(r.get("memory_mb")),
             norm_num(r.get("storage_mb")), norm_num(r.get("gpus")))
            for r in rows
        )
    try:
        if canon(cand_rows) != canon(exceeds):
            errors.append("CANDIDATE_RESOURCE_ROWS_DO_NOT_MATCH_SOURCE")
    except Exception:
        errors.append("CANDIDATE_RESOURCE_ROWS_NONNUMERIC")

    score = spec.get("frozen_score_math") or {}
    trials = score.get("trials_per_task")
    required = score.get("required_successes")
    current = score.get("current_remaining_creditable_tasks")
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (trials, required, current)):
        errors.append("SCORE_MATH_INPUT_INVALID")
        return fail(errors)
    needed = max(0, math.ceil((required - current * trials) / trials))
    if (current, trials, required) != (36, 5, 220):
        errors.append("FROZEN_SCORE_INPUT_MISMATCH")
    if needed != 8 or score.get("additional_creditable_tasks_needed") != 8:
        errors.append("MINIMUM_RECOVERY_COUNT_NOT_8")
    if score.get("current_upper_bound_successes") != 180:
        errors.append("CURRENT_UPPER_BOUND_NOT_180")
    if score.get("reopened_creditable_task_count") != 44 or score.get("reopened_upper_bound_successes") != 220:
        errors.append("REOPENED_BOUND_MISMATCH")

    md = manifest.get("derived") or {}
    if (
        manifest.get("total_task_count") != 66
        or manifest.get("trials_per_task") != 5
        or manifest.get("required_successes") != 220
        or md.get("remaining_creditable_task_count") != 36
        or md.get("maximum_attainable_successes") != 180
        or len(manifest.get("irreversibly_zero_hardware_compatible_tasks", [])) != 18
    ):
        errors.append("ATTAINABILITY_MANIFEST_BASELINE_MISMATCH")
    ar = attain.get("result") or {}
    if ar.get("upper_bound_successes") != 180 or ar.get("required_successes") != 220 or ar.get("attainability_state") != "IMPOSSIBLE":
        errors.append("ATTAINABILITY_VERDICT_BASELINE_MISMATCH")

    envelope = spec.get("minimum_carrier_envelope") or {}
    limits = {"cpus": 8, "memory_mb": 16384, "storage_mb": 51200, "gpus": 0}
    admissible = sorted(
        r["task"] for r in exceeds
        if r["gpus"] == 0 and r["cpus"] <= limits["cpus"]
        and r["memory_mb"] <= limits["memory_mb"] and r["storage_mb"] <= limits["storage_mb"]
    )
    chosen = sorted(spec.get("minimum_recovery_set") or [])
    if len(admissible) != 8 or chosen != admissible:
        errors.append("MINIMUM_RECOVERY_SET_MISMATCH")
    maxima = {
        "cpus_at_least": max(r["cpus"] for r in exceeds if r["task"] in admissible) if admissible else 0,
        "usable_memory_mb_at_least": max(r["memory_mb"] for r in exceeds if r["task"] in admissible) if admissible else 0,
        "free_storage_mb_at_least": max(r["storage_mb"] for r in exceeds if r["task"] in admissible) if admissible else 0,
        "gpus_required": max(r["gpus"] for r in exceeds if r["task"] in admissible) if admissible else 0,
    }
    for k, v in maxima.items():
        if envelope.get(k) != v:
            errors.append("ENVELOPE_MISMATCH:" + k)
    if envelope.get("docker_required") is not True or envelope.get("docker_compose_required") is not True:
        errors.append("CONTAINER_REQUIREMENT_MISMATCH")

    state = spec.get("verification_state") or {}
    if state.get("task_identity_binding_required") is not True:
        errors.append("TASK_IDENTITY_BINDING_MUST_REMAIN_REQUIRED")
    if state.get("concrete_zero_cost_carrier_bound") is not False or state.get("protocol_equivalence_bound") is not False or state.get("attainability_recompiled") is not False:
        errors.append("CANDIDATE_SELF_AUTHORIZATION")
    if spec.get("execution_authority") is not False or spec.get("promotion_authority") is not False:
        errors.append("AUTHORITY_MUST_REMAIN_FALSE")

    if errors:
        return fail(errors)
    return {
        "schema": SCHEMA,
        "status": "PASS__RAW_RESOURCE_METADATA_REPRODUCED__MINIMUM_EIGHT_TASK_CUT_PROVED__TASK_IDENTITY_AND_CARRIER_STILL_UNBOUND__ZERO_CREDIT",
        "pass": True,
        "source_commit": source_commit,
        "reproduced_task_count": task_count,
        "reproduced_resource_exceed_count": len(exceeds),
        "reproduced_gpu_task_count": len(gpu_tasks),
        "minimum_additional_creditable_tasks": 8,
        "minimum_recovery_set": admissible,
        "minimum_carrier_envelope": maxima,
        "projected_creditable_task_count": 44,
        "projected_upper_bound_successes": 220,
        "required_successes": 220,
        "attainability_boundary_reopened_if_carrier_and_task_identity_bind": True,
        "resource_metadata_independently_reproduced": True,
        "task_instruction_files_read": 0,
        "solution_files_read": 0,
        "fresh_acceptance_cases_consumed": 0,
        "task_identity_binding": False,
        "concrete_carrier_bound": False,
        "protocol_equivalence_bound": False,
        "attainability_recompiled": False,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "errors": [],
    }

def main() -> int:
    source_root = Path(os.environ.get("TB4_SOURCE_ROOT", "/tmp/tb4"))
    out = evaluate(
        load(SPEC), load(COMPAT), load(MANIFEST), load(ATTAIN), source_root,
        {"compat": blob_sha(COMPAT), "manifest": blob_sha(MANIFEST), "attain": blob_sha(ATTAIN)},
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
