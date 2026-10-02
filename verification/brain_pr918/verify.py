from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIRROR = ROOT / "verification/brain_pr918/mirror"
CAPSULE = ROOT / "capsules/ceiling_witness_lifter_v1/canonical"

EXPECTED = {
    "runtime": ("verification/brain_pr918/mirror/runtime.py", "c3bbbfa6953c73f9d256466078343ab529a79e3a"),
    "binding": ("verification/brain_pr918/mirror/P1_binding.json", "8703c6aa08227467a619a7ae90d0d61f8e54da39"),
    "binding_verification": ("verification/brain_pr918/mirror/current_binding_verification.json", "3aa8168fc7f81581eea4085504e4a70205949af9"),
    "registry": ("capsules/ceiling_witness_lifter_v1/canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", "ee187f611a0e82b2de495ee377682f39bc31dd31"),
    "protocols": ("capsules/ceiling_witness_lifter_v1/canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json", "eb4bca0fe6a015d49d2854998fbe046c979c7ea9"),
    "executor": ("capsules/ceiling_witness_lifter_v1/canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json", "c61882d69a66f61b4ea1ce6ad14f86fcefd1f76a"),
    "terminal": ("capsules/ceiling_witness_lifter_v1/canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json", "bd86b4c53992b47a4a60b64a60ba03db9a442cfc"),
}

BRAIN_PR = 918
BRAIN_HEAD = "0dcdd42381cac34320ce43639a4354b9064d919e"
FAMILY = "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
BINDING_PATH = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"


def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\x00" + b).hexdigest()


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def require_exact_blobs() -> None:
    for label, (rel, expected) in EXPECTED.items():
        got = blob_sha(ROOT / rel)
        if got != expected:
            raise AssertionError(f"{label}: blob mismatch {got} != {expected}")


def load_runtime():
    path = ROOT / EXPECTED["runtime"][0]
    spec = importlib.util.spec_from_file_location("brain_pr918_runtime", path)
    if spec is None or spec.loader is None:
        raise AssertionError("runtime import spec unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base_args():
    return dict(
        family=FAMILY,
        behavior_id=BEHAVIOR,
        binding_path=BINDING_PATH,
        binding_blob_sha=EXPECTED["binding"][1],
        protocols=load_json(EXPECTED["protocols"][0]),
        registry=load_json(EXPECTED["registry"][0]),
        binding=load_json(EXPECTED["binding"][0]),
        current_binding_verification=load_json(EXPECTED["binding_verification"][0]),
        executor_manifest=load_json(EXPECTED["executor"][0]),
        terminal_result=load_json(EXPECTED["terminal"][0]),
    )


def must_fail(mod, args, reason: str) -> None:
    out = mod.evaluate(**args)
    if out.get("pass") is not False:
        raise AssertionError(f"mutation survived: {reason}: {out}")


def main() -> int:
    require_exact_blobs()
    mod = load_runtime()
    args = base_args()
    out = mod.evaluate(**args)

    assert out["pass"] is True, out
    assert out["status"] == "CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED", out
    assert out["source_parent_receipt_count"] == 2, out
    assert out["source_case_count"] == 60, out
    witness = out["candidate_witness"]
    assert witness["family"] == FAMILY
    assert witness["source_portfolios"] == ["T0", "T2"]
    assert witness["scope_relation"] == "PROVEN_STRONGER"
    assert witness["closes_entire_protocol"] is True
    assert witness["result"]["brain_lower_bound"] == 1.0
    assert witness["result"]["theoretical_upper_bound"] == 1.0
    assert witness["verified"] is False
    assert witness["independent"] is False
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["promotion_authority"] is False
    assert out["new_reality_units_consumed"] == 0

    x = base_args()
    x["registry"] = copy.deepcopy(x["registry"])
    x["registry"]["family_to_residual_contracts"][FAMILY] = [BEHAVIOR, "OTHER"]
    must_fail(mod, x, "partial-family mapping")

    x = base_args()
    x["current_binding_verification"] = copy.deepcopy(x["current_binding_verification"])
    for row in x["current_binding_verification"]["verified_jobs"]:
        if row.get("behavior_id") == BEHAVIOR:
            row["binding_blob_sha"] = "0" * 40
    must_fail(mod, x, "binding identity tamper")

    x = base_args()
    x["terminal_result"] = copy.deepcopy(x["terminal_result"])
    rows = x["terminal_result"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
    for row in rows:
        if row.get("behavior_id") == BEHAVIOR:
            row["direct_instrumentation_pass"] = False
    must_fail(mod, x, "direct instrumentation failure")

    x = base_args()
    x["terminal_result"] = copy.deepcopy(x["terminal_result"])
    rows = x["terminal_result"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T2"]
    x["terminal_result"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T2"] = [
        r for r in rows if r.get("behavior_id") != BEHAVIOR
    ]
    must_fail(mod, x, "missing T2 load-bearing receipt")

    x = base_args()
    x["terminal_result"] = copy.deepcopy(x["terminal_result"])
    x["terminal_result"]["direct_terminal_population"]["routes"][BEHAVIOR] = {"cases": 60, "passes": 60}
    must_fail(mod, x, "duplicate standalone direct route")

    x = base_args()
    x["binding"] = copy.deepcopy(x["binding"])
    x["binding"]["terminal_acceptance"]["any_load_bearing_p1_failure_blocks_behavior_proof"] = False
    must_fail(mod, x, "load-bearing failure made nonfatal")

    result = {
        "schema": "PROJECT_BRAIN_PR918_PARENT_MULTIPLEX_CEILING_PUBLIC_VERIFICATION_V1",
        "status": "INDEPENDENT_PUBLIC_RUNNER_PASS",
        "brain_pr": BRAIN_PR,
        "brain_head": BRAIN_HEAD,
        "family": FAMILY,
        "behavior_id": BEHAVIOR,
        "exact_blobs": {k: v[1] for k, v in EXPECTED.items()},
        "candidate_status": out["status"],
        "source_parent_receipt_count": out["source_parent_receipt_count"],
        "source_case_count": out["source_case_count"],
        "brain_lower_bound": witness["result"]["brain_lower_bound"],
        "theoretical_upper_bound": witness["result"]["theoretical_upper_bound"],
        "mutations_killed": 6,
        "fresh_terminal_evidence_consumed": 0,
        "terminal_replay": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "incremental_spend_usd": 0,
    }
    print("RESULT_JSON=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
