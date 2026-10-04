from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime.unknown_domain_direct_production_preflight_v1 import preflight

ROOT = Path(__file__).resolve().parent
SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_V2_ONE_USE_PRODUCTION_EXECUTION_V1"
TARGET = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
RESULT_PATH = ROOT / "unknown_domain_v2_production_execution_result_20261005.json"

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_production_preflight_v1.py": "e1365ccdba308c529f182797cf68075b2f1dc07c",
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PRECOMMIT_V1.json": "ddf55f3e54ef6af89a95395075441742cb124258",
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json": "337bb7ee777e8b0f7f6340f395ca6c50e466594c",
    "canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json": "36452412fb60ce38405f139111eba98b5cebc040",
    "canonical/verification/UNKNOWN_DOMAIN_V2_FINAL_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json": "93353244a5a0a6a7ef2e1e0a3a1bbedb63cef3ec",
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def load_json(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text())

def recheck_exact_bytes() -> dict[str, str]:
    actual = {}
    for rel, expected in EXPECTED.items():
        got = git_blob_sha((ROOT / rel).read_bytes())
        if got != expected:
            raise RuntimeError(f"EXACT_BLOB_MISMATCH:{rel}:{got}:{expected}")
        actual[rel] = got
    return actual

def build_preflight_input() -> tuple[dict[str, Any], dict[str, str]]:
    exact = recheck_exact_bytes()
    qualification = load_json("canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
    activation = load_json("canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json")
    activation_verification = load_json("canonical/verification/UNKNOWN_DOMAIN_V2_FINAL_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

    qualification_ok = (
        qualification.get("target_predicate") == TARGET
        and str(qualification.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
        and qualification.get("verified_result", {}).get("all_fresh_cases_pass") is True
        and qualification.get("verified_result", {}).get("fresh_hidden_scored_cases") == 81
        and qualification.get("verified_result", {}).get("persistent_learned_bytes") == 0
        and qualification.get("verified_result", {}).get("production_cases_generated") == 0
    )
    activation_ok = (
        activation.get("active") is True
        and activation.get("target_predicate") == TARGET
        and activation.get("authority", {}).get("execution") is True
        and activation.get("authority", {}).get("predicate_local_fresh_reality") is True
        and activation.get("authority", {}).get("global_fresh_reality") is False
        and activation.get("authority", {}).get("promotion") is False
        and activation.get("authority", {}).get("acceptance_credit") is False
    )
    activation_verification_ok = (
        activation_verification.get("target_predicate") == TARGET
        and str(activation_verification.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
        and activation_verification.get("verified_activation", {}).get("git_blob_sha")
            == EXPECTED["canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json"]
        and activation_verification.get("independent_runner", {}).get("conclusion") == "success"
    )

    doc = {
        "qualification_independent_pass": qualification_ok,
        "exact_subject_blobs_rechecked": True,
        "production_cases_consumed": 0,
        "production_beacon_generated": False,
        "candidate_mutated_after_qualification": False,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "incremental_spend_usd": 0,
        "target_predicate": TARGET,
        "authorized_leaves": activation.get("authorized_leaves"),
        "predicate_local_activation_independent_pass": activation_verification_ok and activation_ok,
        "predicate_local_fresh_reality": activation.get("authority", {}).get("predicate_local_fresh_reality"),
        "global_fresh_reality": activation.get("authority", {}).get("global_fresh_reality"),
        "one_use_claim_created": False,
        "execution_started": False,
    }
    return doc, exact

def execution_lease(exact: Mapping[str, str]) -> dict[str, Any]:
    executor_blob = git_blob_sha(Path(__file__).read_bytes())
    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V2_EXACT_EXECUTION_LEASE_V1",
        "target_predicate": TARGET,
        "runner_repository": os.environ.get("GITHUB_REPOSITORY", "moxnixmdj/verification-capsule-runner"),
        "executor_path": Path(__file__).name,
        "executor_git_blob_sha": executor_blob,
        "exact_frozen_subject_blobs": dict(sorted(exact.items())),
        "production_populations_allowed": 1,
        "production_cases_allowed": 27,
        "max_transfer_probes_per_case": 2,
        "replay_allowed": False,
        "replacement_allowed": False,
        "post_result_tuning_allowed": False,
        "global_fresh_reality": False,
        "incremental_spend_usd": 0,
    }

def claim_ref_for_lease(lease: Mapping[str, Any]) -> tuple[str, str]:
    digest = sha256_json(lease)
    return digest, "refs/heads/unknown-domain-direct-claims/" + digest

def create_atomic_claim(claim_ref: str) -> tuple[int, dict[str, Any]]:
    token = os.environ.get("GH_TOKEN")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    if not token or not repo or not sha:
        raise RuntimeError("GITHUB_CLAIM_ENV_MISSING")
    payload = json.dumps({"ref": claim_ref, "sha": sha}).encode()
    req = urllib.request.Request(
        f"{api}/repos/{repo}/git/refs",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode() or "{}")
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            body = json.loads(raw or "{}")
        except json.JSONDecodeError:
            body = {"raw": raw}
        return int(exc.code), body

def write_result(doc: Mapping[str, Any]) -> None:
    RESULT_PATH.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n")

def execute_production() -> dict[str, Any]:
    preflight_input, exact = build_preflight_input()
    pre = preflight(preflight_input)
    if pre.get("ready") is not True:
        result = {
            "schema": SCHEMA,
            "status": "ABORTED_BEFORE_CLAIM__PREFLIGHT_FAIL",
            "preflight": pre,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
        }
        write_result(result)
        return result

    lease = execution_lease(exact)
    lease_digest, claim_ref = claim_ref_for_lease(lease)
    claim_status, claim_response = create_atomic_claim(claim_ref)

    if claim_status != 201:
        result = {
            "schema": SCHEMA,
            "status": "ABORTED_BEFORE_BEACON__ATOMIC_CLAIM_NON201",
            "preflight": pre,
            "execution_lease": lease,
            "execution_lease_digest_sha256": lease_digest,
            "claim_ref": claim_ref,
            "claim_create_http_status": claim_status,
            "claim_response_message": claim_response.get("message"),
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "replay_attempted": False,
        }
        write_result(result)
        return result

    # Irreversible boundary crossed. Fresh entropy is intentionally created only now.
    import secrets

    beacon = "UDIR-PRODUCTION-" + secrets.token_hex(32)
    evaluator_secret = secrets.token_bytes(32)
    activation = load_json("canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json")
    authority = {
        "active": True,
        "target_predicate": TARGET,
        "authorized_leaves": activation["authorized_leaves"],
        "predicate_local_fresh_reality": True,
        "global_fresh_reality": False,
        "one_use_claim_created": True,
        "one_use_claim_id": claim_ref,
        "incremental_spend_usd": 0,
    }
    packet = generator.generate_production_population(
        beacon=beacon,
        evaluator_secret=evaluator_secret,
        authority=authority,
    )

    case_results = []
    scorer_rows = []
    execution_error_count = 0
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
        row = {"case_id": visible.get("case_id"), "leaf_id": visible.get("leaf_id")}
        try:
            out = harness.execute_case(
                candidate_step=candidate.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            row.update({
                "probe_count": out.get("probe_count"),
                "candidate_terminal_action": out.get("candidate_terminal_action"),
                "scorer_result": out.get("scorer_result"),
            })
            scorer_rows.append(out["scorer_result"])
        except Exception as exc:
            execution_error_count += 1
            row["execution_error"] = type(exc).__name__ + ":" + str(exc)
        case_results.append(row)

    if execution_error_count == 0 and len(scorer_rows) == 27:
        aggregate = scorer.aggregate(scorer_rows)
    else:
        aggregate = {
            "status": "EXECUTION_ERRORS_PRESENT",
            "all_27_cases_pass": False,
            "transfer_leaf_pass": False,
            "abstention_leaf_pass": False,
            "case_count": 27,
            "execution_error_count": execution_error_count,
            "separate_independent_reduction_required": True,
        }

    result = {
        "schema": SCHEMA,
        "status": "ONE_USE_PRODUCTION_EXECUTED__INDEPENDENT_RESULT_REDUCTION_REQUIRED",
        "target_predicate": TARGET,
        "preflight": pre,
        "execution_lease": lease,
        "execution_lease_digest_sha256": lease_digest,
        "claim_ref": claim_ref,
        "claim_create_http_status": claim_status,
        "claim_response_ref": claim_response.get("ref"),
        "claim_response_object_sha": (claim_response.get("object") or {}).get("sha"),
        "beacon_sha256": hashlib.sha256(beacon.encode()).hexdigest(),
        "evaluator_secret_commitment_sha256": hashlib.sha256(evaluator_secret).hexdigest(),
        "visible_packet_digest": packet["visible_packet_digest"],
        "hidden_packet_digest": packet["hidden_packet_digest"],
        "authority_claim_id": packet.get("authority_claim_id"),
        "production": packet.get("production"),
        "production_cases_generated": packet.get("case_count"),
        "terminal_cases_consumed": 27,
        "case_level_results": case_results,
        "aggregate_from_frozen_scorer": aggregate,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "incremental_spend_usd": 0,
        "global_fresh_reality": False,
        "promotion_authority": False,
        "acceptance_credit": False,
        "replay_allowed": False,
        "replacement_allowed": False,
        "post_result_tuning_allowed": False,
    }
    write_result(result)
    return result

if __name__ == "__main__":
    result = execute_production()
    print(json.dumps({
        "status": result.get("status"),
        "claim_create_http_status": result.get("claim_create_http_status"),
        "terminal_cases_consumed": result.get("terminal_cases_consumed"),
        "all_27_cases_pass": (result.get("aggregate_from_frozen_scorer") or {}).get("all_27_cases_pass"),
        "result_path": str(RESULT_PATH),
    }, sort_keys=True))
    if str(result.get("status", "")).startswith("ABORTED"):
        raise SystemExit(2)
