from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "authority_epoch_v4_20261005"

ORIGINAL_TO_LOCAL = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "CURRENT_TERMINAL_AUTHORITY_V1.json",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json": "TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V14_ACTIVATION_V1.json": "CURRENT_ZERO_REALITY_MINIMUM_CUT_V14_ACTIVATION_V1.json",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V14.json": "CURRENT_ZERO_REALITY_MINIMUM_CUT_V14.json",
}

BRAIN_SOURCE_REF = "b63f869b1d0c910ffce69269b164c3ef6c1368ec"
CANDIDATE_REF = "d77219c62a3a4e6b49351f97ccd9becce43ab19b"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def compute_epoch(blob_map: dict[str, str]) -> str:
    payload = "".join(f"{path}={sha}\n" for path, sha in sorted(blob_map.items()))
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> int:
    candidate = json.loads((SUBJECT / "AUTHORITY_EPOCH_PREEMPTION_V4.json").read_text(encoding="utf-8"))
    declared = candidate["epoch_components"]
    actual: dict[str, str] = {}
    errors: list[str] = []

    for original, local_name in ORIGINAL_TO_LOCAL.items():
        data = (SUBJECT / local_name).read_bytes()
        actual[original] = git_blob_sha(data)
        if declared.get(original) != actual[original]:
            errors.append(
                f"BLOB_MISMATCH:{original}:declared={declared.get(original)}:actual={actual[original]}"
            )

    epoch = compute_epoch(actual)
    expected_epoch = candidate["start_authority_epoch_sha256"]
    if epoch != expected_epoch:
        errors.append(f"EPOCH_MISMATCH:expected={expected_epoch}:actual={epoch}")

    required_false = ("execution_authority", "promotion_authority", "fresh_reality_authority")
    for key in required_false:
        if candidate.get(key) is not False:
            errors.append(f"AUTHORITY_FLAG_NOT_FALSE:{key}:{candidate.get(key)!r}")

    out = {
        "schema": "PROJECT_BRAIN_AUTHORITY_EPOCH_V4_PUBLIC_RUNNER_VERIFICATION_V1",
        "status": "PASS__EXACT_BYTES_AND_EPOCH_MATCH__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "brain_source_ref": BRAIN_SOURCE_REF,
        "candidate_ref": CANDIDATE_REF,
        "candidate_blob_sha": git_blob_sha((SUBJECT / "AUTHORITY_EPOCH_PREEMPTION_V4.json").read_bytes()),
        "expected_epoch_sha256": expected_epoch,
        "actual_epoch_sha256": epoch,
        "declared_components": declared,
        "actual_components": actual,
        "errors": errors,
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
