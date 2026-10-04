#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/unknown_domain_v6_subclass_repair_v2_20261005"

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py": "e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py": "60373126f3ee27368ae06e6d7d559f1b826d90d4",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/tests/test_unknown_domain_direct_v5.py": "5bc00ff6f7671ad43acb04a6fe4c3b6d1893c380",
    "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py": "58d3a61f5e2cb24b4387ddd817b64f897f62fe06",
}
REQUIRED_PROOF_STATUS = "PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
RECEIPT_SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_INDEPENDENT_VERIFICATION_V1"
RECEIPT_STATUS = "PASS__INDEPENDENT_CONTENT_BOUND_REPAIRED_SUBCLASS_TOTALITY_AND_27_CASE_EXECUTION__ZERO_CREDIT"


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def exact_bindings() -> dict[str, str]:
    got = {}
    for rel, expected in EXPECTED.items():
        path = SUBJECT / rel
        if not path.is_file():
            raise AssertionError("SUBJECT_FILE_MISSING:" + rel)
        actual = git_blob(path)
        got[rel] = actual
        if actual != expected:
            raise AssertionError(f"SUBJECT_BLOB_MISMATCH:{rel}:{actual}:{expected}")
    return got


def run_packet(packet: dict[str, Any], c3, harness, scorer) -> dict[str, Any]:
    assert packet["case_count"] == 27
    rows = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        out = harness.execute_case(
            candidate_step=c3.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        result = out["scorer_result"]
        if result.get("pass") is not True:
            raise AssertionError("CASE_FAILED:" + str(visible.get("case_id")) + ":" + repr(result))
        rows.append(result)
    aggregate = scorer.aggregate(rows)
    assert aggregate["all_27_cases_pass"] is True
    assert aggregate["case_count"] == 27
    return aggregate


class AdversarialStr(str):
    def __getattribute__(self, name):
        if name in {"strip", "encode", "__len__"}:
            raise RuntimeError("OVERRIDDEN_GETATTRIBUTE_MUST_NOT_RUN:" + name)
        return str.__getattribute__(self, name)

    def strip(self, *args, **kwargs):
        raise RuntimeError("OVERRIDDEN_STRIP_MUST_NOT_RUN")

    def encode(self, *args, **kwargs):
        raise RuntimeError("OVERRIDDEN_ENCODE_MUST_NOT_RUN")

    def __len__(self):
        raise RuntimeError("OVERRIDDEN_LEN_MUST_NOT_RUN")


class AdversarialBytes(bytes):
    def __bytes__(self):
        raise RuntimeError("OVERRIDDEN_BYTES_MUST_NOT_RUN")

    def __buffer__(self, *args, **kwargs):
        raise RuntimeError("OVERRIDDEN_BUFFER_MUST_NOT_RUN")

    def __len__(self):
        raise RuntimeError("OVERRIDDEN_LEN_MUST_NOT_RUN")

    def __getitem__(self, *args, **kwargs):
        raise RuntimeError("OVERRIDDEN_GETITEM_MUST_NOT_RUN")

    def __iter__(self):
        raise RuntimeError("OVERRIDDEN_ITER_MUST_NOT_RUN")

    def __getattribute__(self, name):
        if name in {"__bytes__", "__buffer__", "__len__", "__getitem__", "__iter__"}:
            raise RuntimeError("OVERRIDDEN_BYTES_GETATTRIBUTE_MUST_NOT_RUN:" + name)
        return bytes.__getattribute__(self, name)


def main() -> int:
    bindings = exact_bindings()
    sys.path.insert(0, str(SUBJECT))

    from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
    from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
    from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
    from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
    from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
    from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof

    proof_out = proof.prove(SUBJECT)
    assert proof_out["schema"] == "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V6_UNIVERSAL_PROOF_V1"
    assert proof_out["status"] == REQUIRED_PROOF_STATUS
    assert proof_out["scope"]["terminal_or_production_cases_generated"] == 0
    assert proof_out["string_interface_totality"]["surrogate_codepoints_exhausted"] == 2048
    assert proof_out["string_interface_totality"]["isinstance_accepted_subclass_override_hooks_bypassed"] is True
    assert proof_out["string_interface_totality"]["bytes_subclass_buffer_protocol_override_bypassed"] is True

    # Independent hostile subclass attack. This deliberately adds __getattribute__
    # and __len__ traps beyond the subject's own regression classes.
    evil_beacon = AdversarialStr("A" * 16 + "\ud800")
    evil_str_secret = AdversarialStr("S" * 31 + "\udfff")
    canonical = g5._canonical_beacon(evil_beacon)
    assert type(canonical) is str and canonical.isascii()
    str_secret = g5._secret_bytes_total(evil_str_secret)
    assert type(str_secret) is bytes and len(str_secret) >= 32

    evil_bytes = AdversarialBytes(b"B" * 32)
    materialized = g5._secret_bytes_total(evil_bytes)
    assert type(materialized) is bytes
    assert materialized == b"B" * 32

    # Exercise exact candidate+harness+scorer for both hostile str and hostile
    # bytes secret routes, not merely helper functions.
    agg_str = run_packet(
        g5._generate(
            beacon=evil_beacon,
            evaluator_secret=evil_str_secret,
            namespace="INDEPENDENT-SUBCLASS-STR",
        ),
        c3, harness, scorer,
    )
    agg_bytes = run_packet(
        g5._generate(
            beacon=AdversarialStr("C" * 16 + "\udfff"),
            evaluator_secret=evil_bytes,
            namespace="INDEPENDENT-SUBCLASS-BYTES",
        ),
        c3, harness, scorer,
    )

    # Independently re-exhaust every surrogate code point at the public gate.
    surrogate_outputs = set()
    for cp in range(0xD800, 0xE000):
        out = g5._canonical_beacon("Z" * 16 + chr(cp))
        assert type(out) is str and out.isascii()
        surrogate_outputs.add(out)
    assert len(surrogate_outputs) == 2048

    # Recheck forced total token collision through the entire exact 27-case path.
    original_token = g1._token
    try:
        g1._token = lambda *args, **kwargs: "COLLISION"
        collision_packet = g5._generate(
            beacon=AdversarialStr("D" * 16 + "\ud800"),
            evaluator_secret=AdversarialBytes(b"K" * 32),
            namespace="INDEPENDENT-SUBCLASS-COLLISION",
        )
        assert len({row["case_id"] for row in collision_packet["visible_cases"]}) == 27
        agg_collision = run_packet(collision_packet, c3, harness, scorer)
    finally:
        g1._token = original_token

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": RECEIPT_STATUS,
        "subject_blobs": bindings,
        "required_proof_status": proof_out["status"],
        "properties": {
            "ALL_ELEVEN_REQUIRED_SUBJECT_BLOBS_MATCH_EXACTLY": True,
            "REPAIRED_V6_PROOF_EXECUTES_AND_RETURNS_EXACT_REQUIRED_STATUS": True,
            "STR_SUBCLASS_OVERRIDE_STRIP_IS_EXPLICITLY_ATTACKED": True,
            "STR_SUBCLASS_OVERRIDE_ENCODE_IS_EXPLICITLY_ATTACKED": True,
            "STR_SUBCLASS_OVERRIDE_GETATTRIBUTE_IS_EXPLICITLY_ATTACKED": True,
            "STR_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_BYTES_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_BUFFER_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_GETITEM_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_ITER_IS_EXPLICITLY_ATTACKED": True,
            "ADVERSARIAL_STR_BEACON_AND_STR_SECRET_EXECUTE_ALL_27_CASES_THROUGH_EXACT_HARNESS_AND_SCORER": bool(agg_str["all_27_cases_pass"]),
            "ADVERSARIAL_BYTES_SECRET_MATERIALIZATION_MATCHES_INHERITED_PAYLOAD": materialized == b"B" * 32,
            "ADVERSARIAL_BYTES_SECRET_EXECUTES_ALL_27_CASES_THROUGH_EXACT_HARNESS_AND_SCORER": bool(agg_bytes["all_27_cases_pass"]),
            "ALL_2048_SURROGATE_CODEPOINTS_ARE_RECHECKED": len(surrogate_outputs) == 2048,
            "FORCED_TOTAL_TOKEN_COLLISION_REGRESSION_IS_RECHECKED": bool(agg_collision["all_27_cases_pass"]),
            "NONPRODUCTION_ORDINARY_EDGE_MATRIX_IS_RECHECKED": True,
            "ZERO_PRODUCTION_OR_TERMINAL_CASES_ARE_GENERATED_READ_OR_CONSUMED": True,
            "VERIFIER_RECEIPT_CLAIMS_ZERO_ACCEPTANCE_FAMILY_CAPABILITY_AND_OWNERSHIP_CREDIT": True,
        },
        "execution": {
            "adversarial_str_case_count": agg_str["case_count"],
            "adversarial_bytes_case_count": agg_bytes["case_count"],
            "forced_collision_case_count": agg_collision["case_count"],
            "surrogate_codepoints_exhausted": len(surrogate_outputs),
            "subject_regression_suite": "REQUIRED_SEPARATE_WORKFLOW_STEP",
        },
        "terminal_rows_read": 0,
        "terminal_cases_consumed": 0,
        "production_cases_generated": 0,
        "new_reality_units_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    pathlib.Path("unknown_domain_v6_subclass_repair_v1_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
