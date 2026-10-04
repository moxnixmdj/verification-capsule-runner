#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "unknown_domain_v6_20261005"
BRAIN_REPAIR_BRANCH_HEAD = "486b44073e4b7250025302c55682c476a434a321"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py": "e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py": "60373126f3ee27368ae06e6d7d559f1b826d90d4",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py": "58d3a61f5e2cb24b4387ddd817b64f897f62fe06",
    "canonical/tests/test_unknown_domain_direct_v5.py": "5bc00ff6f7671ad43acb04a6fe4c3b6d1893c380",
}

RECEIPT_SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_INDEPENDENT_VERIFICATION_V1"
RECEIPT_STATUS = "PASS__INDEPENDENT_CONTENT_BOUND_REPAIRED_SUBCLASS_TOTALITY_AND_27_CASE_EXECUTION__ZERO_CREDIT"


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require_runtime_error(label, fn) -> None:
    try:
        fn()
    except RuntimeError:
        return
    raise AssertionError("EXPECTED_ADVERSARIAL_OVERRIDE_TO_RAISE:" + label)


def main() -> int:
    observed = {}
    for rel, expected in EXPECTED_BLOBS.items():
        got = git_blob_sha(SUBJECT / rel)
        assert got == expected, ("SUBJECT_BLOB_MISMATCH", rel, got, expected)
        observed[rel] = got

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
    from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
    from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
    from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
    from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof

    universal = proof.prove(SUBJECT)
    assert universal["schema"] == "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V6_UNIVERSAL_PROOF_V1"
    assert universal["status"] == "PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
    assert universal["exact_subject_blobs"]["canonical/runtime/unknown_domain_direct_hidden_generator_v5.py"] == EXPECTED_BLOBS["canonical/runtime/unknown_domain_direct_hidden_generator_v5.py"]
    assert universal["exact_subject_blobs"]["canonical/tests/test_unknown_domain_direct_v5.py"] == EXPECTED_BLOBS["canonical/tests/test_unknown_domain_direct_v5.py"]
    assert universal["string_interface_totality"]["surrogate_codepoints_exhausted"] == 2048
    assert universal["string_interface_totality"]["isinstance_accepted_subclass_override_hooks_bypassed"] is True
    assert universal["string_interface_totality"]["bytes_subclass_buffer_protocol_override_bypassed"] is True
    assert universal["identifier_totality_proof"]["forced_total_token_collision_survives_construction"] is True
    assert universal["transfer_proof"]["all_six_families_universal"] is True
    assert universal["abstention_proof"]["all_three_classes_universal"] is True
    assert universal["scope"]["terminal_or_production_cases_generated"] == 0

    class HostileStr(str):
        def __getattribute__(self, name):
            if name in {"strip", "encode"}:
                raise RuntimeError("OVERRIDDEN_GETATTRIBUTE_MUST_NOT_RUN")
            return object.__getattribute__(self, name)

        def strip(self, *args, **kwargs):
            raise RuntimeError("OVERRIDDEN_STRIP_MUST_NOT_RUN")

        def encode(self, *args, **kwargs):
            raise RuntimeError("OVERRIDDEN_ENCODE_MUST_NOT_RUN")

        def __len__(self):
            raise RuntimeError("OVERRIDDEN_LEN_MUST_NOT_RUN")

    class HostileBytes(bytes):
        def __getattribute__(self, name):
            if name in {"__bytes__", "__buffer__", "__getitem__", "__iter__"}:
                raise RuntimeError("OVERRIDDEN_GETATTRIBUTE_MUST_NOT_RUN")
            return object.__getattribute__(self, name)

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

    hostile_beacon = HostileStr("A" * 16 + "\ud800")
    hostile_secret_text = HostileStr("S" * 31 + "\udfff")
    hostile_secret_bytes = HostileBytes(b"B" * 32)

    require_runtime_error("STR_GETATTRIBUTE_STRIP", lambda: hostile_beacon.strip())
    require_runtime_error("STR_GETATTRIBUTE_ENCODE", lambda: hostile_beacon.encode())
    require_runtime_error("STR_LEN", lambda: len(hostile_beacon))
    require_runtime_error("BYTES_GETATTRIBUTE_BYTES", lambda: hostile_secret_bytes.__bytes__())
    require_runtime_error("BYTES_LEN", lambda: len(hostile_secret_bytes))
    require_runtime_error("BYTES_GETATTRIBUTE_GETITEM", lambda: hostile_secret_bytes[0])
    require_runtime_error("BYTES_GETATTRIBUTE_ITER", lambda: iter(hostile_secret_bytes))

    # Base descriptors must read inherited immutable payloads without dispatching
    # through the adversarial instance hooks above.
    canonical = g5._canonical_beacon(hostile_beacon)
    assert canonical.isascii()
    assert canonical.startswith("UDIRV5-BEACON-HEX|")
    assert g5._secret_bytes_total(hostile_secret_text)
    assert g5._secret_bytes_total(hostile_secret_bytes) == b"B" * 32

    def execute_packet(packet):
        rows = []
        for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
            out = harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            assert out["scorer_result"]["pass"] is True, (visible["case_id"], out)
            rows.append(out["scorer_result"])
        agg = scorer.aggregate(rows)
        assert agg["all_27_cases_pass"] is True
        return len(rows)

    adversarial_cases = 0
    packet = g5._generate(
        beacon=hostile_beacon,
        evaluator_secret=hostile_secret_text,
        namespace="INDEPENDENT-HOSTILE-STR",
    )
    adversarial_cases += execute_packet(packet)

    packet = g5._generate(
        beacon=hostile_beacon,
        evaluator_secret=hostile_secret_bytes,
        namespace="INDEPENDENT-HOSTILE-BYTES",
    )
    adversarial_cases += execute_packet(packet)
    assert adversarial_cases == 54

    ordinary_beacons = [
        "A" * 16 + "\ud800",
        "\udfff" + "B" * 16,
        "Ω" * 16,
        "\x00" + "C" * 16,
    ]
    ordinary_secrets = [
        b"S" * 32,
        "T" * 31 + "\ud800",
        "\udfff" + "U" * 31,
        "λ" * 32,
    ]
    ordinary_populations = 0
    ordinary_cases = 0
    for i, beacon in enumerate(ordinary_beacons):
        for j, secret in enumerate(ordinary_secrets):
            packet = g5._generate(
                beacon=beacon,
                evaluator_secret=secret,
                namespace=f"INDEPENDENT-EDGE-{i}-{j}",
            )
            ordinary_cases += execute_packet(packet)
            ordinary_populations += 1
    assert ordinary_populations == 16
    assert ordinary_cases == 432

    attacked = {
        "STR_SUBCLASS_OVERRIDE_STRIP_IS_EXPLICITLY_ATTACKED": True,
        "STR_SUBCLASS_OVERRIDE_ENCODE_IS_EXPLICITLY_ATTACKED": True,
        "STR_SUBCLASS_OVERRIDE_GETATTRIBUTE_IS_EXPLICITLY_ATTACKED": True,
        "STR_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED": True,
        "BYTES_SUBCLASS_OVERRIDE_BYTES_IS_EXPLICITLY_ATTACKED": True,
        "BYTES_SUBCLASS_OVERRIDE_BUFFER_IS_EXPLICITLY_ATTACKED": True,
        "BYTES_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED": True,
        "BYTES_SUBCLASS_OVERRIDE_GETITEM_IS_EXPLICITLY_ATTACKED": True,
        "BYTES_SUBCLASS_OVERRIDE_ITER_IS_EXPLICITLY_ATTACKED": True,
    }
    assert all(attacked.values())

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": RECEIPT_STATUS,
        "brain_repair_branch_head": BRAIN_REPAIR_BRANCH_HEAD,
        "subject_blobs": observed,
        "universal_proof_status": universal["status"],
        "subclass_attack_properties": attacked,
        "adversarial_execution": {
            "populations": 2,
            "cases": adversarial_cases,
            "all_27_case_exact_scorer_pass_per_population": True,
        },
        "ordinary_nonproduction_edge_matrix": {
            "populations": ordinary_populations,
            "cases": ordinary_cases,
            "all_pass": True,
        },
        "universal_rechecks": {
            "surrogate_codepoints_exhausted": 2048,
            "forced_total_token_collision": True,
            "all_six_transfer_families": True,
            "all_three_abstention_classes": True,
        },
        "production_or_terminal_cases_generated_read_or_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    out = ROOT / "unknown_domain_v6_subclass_repair_verification.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
