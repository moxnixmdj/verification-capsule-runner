#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "unknown_domain_v6_20261005"
BRAIN_SUBJECT_COMMIT = "HARDENED_REPAIR_GATE_63f8a508ee42fd45721f1b94f0adeb2ed43a0a81"

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

def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main() -> int:
    observed = {}
    for rel, expected in EXPECTED_BLOBS.items():
        got = git_blob_sha(SUBJECT / rel)
        assert got == expected, (rel, got, expected)
        observed[rel] = got

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
    from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
    from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
    from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
    from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
    from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof

    result = proof.prove(SUBJECT)
    assert result["status"] == "PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
    assert result["scope"]["terminal_or_production_cases_generated"] == 0
    assert result["string_interface_totality"]["surrogate_codepoints_exhausted"] == 2048
    assert result["identifier_totality_proof"]["forced_total_token_collision_survives_construction"] is True
    assert result["transfer_proof"]["all_six_families_universal"] is True
    assert result["transfer_proof"]["add2_exact_float_order_repaired"] is True
    assert result["abstention_proof"]["all_three_classes_universal"] is True

    beacon = "A" * 16 + "\ud800"
    try:
        g4._generate(beacon=beacon, evaluator_secret=b"x" * 32, namespace="V4FAIL")
    except UnicodeEncodeError:
        v4_counterexample = True
    else:
        raise AssertionError("EXPECTED_V4_STRICT_UTF8_COUNTEREXAMPLE")

    class AdversarialStr(str):
        def strip(self, *args, **kwargs):
            raise RuntimeError("OVERRIDDEN_STRIP_MUST_NOT_RUN")
        def encode(self, *args, **kwargs):
            raise RuntimeError("OVERRIDDEN_ENCODE_MUST_NOT_RUN")

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

    subclass_packet = g5._generate(
        beacon=AdversarialStr("A" * 16 + "\ud800"),
        evaluator_secret=AdversarialStr("S" * 31 + "\udfff"),
        namespace="VERIFY-SUBCLASS-STR",
    )
    subclass_rows = []
    for visible, hidden in zip(subclass_packet["visible_cases"], subclass_packet["hidden_records"], strict=True):
        out = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True, (visible["case_id"], out)
        subclass_rows.append(out["scorer_result"])
    assert scorer.aggregate(subclass_rows)["all_27_cases_pass"] is True

    subclass_secret = AdversarialBytes(b"B" * 32)
    assert g5._secret_bytes_total(subclass_secret) == b"B" * 32

    beacons = ["A" * 16 + "\ud800", "\udfff" + "B" * 16, "Ω" * 16, "\x00" + "C" * 16]
    secrets = [b"S" * 32, "T" * 31 + "\ud800", "\udfff" + "U" * 31, "λ" * 32]
    populations = 0
    cases = 0
    for i, b in enumerate(beacons):
        for j, s in enumerate(secrets):
            packet = g5._generate(beacon=b, evaluator_secret=s, namespace=f"VERIFY-{i}-{j}")
            rows = []
            for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
                out = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
                assert out["scorer_result"]["pass"] is True, (visible["case_id"], out)
                rows.append(out["scorer_result"])
                cases += 1
            assert scorer.aggregate(rows)["all_27_cases_pass"] is True
            populations += 1
    assert populations == 16
    assert cases == 432

    receipt = {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_TOTAL_EXACT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__INDEPENDENT_CONTENT_BOUND_TOTAL_STRING_STRUCTURAL_ID_EXACT_FLOAT_AND_432_CASE_FALSIFICATION__ZERO_CREDIT",
        "brain_subject_commit": BRAIN_SUBJECT_COMMIT,
        "subject_blobs": observed,
        "universal_theorem_status": result["status"],
        "surrogate_codepoints_exhausted": 2048,
        "structural_identifier_totality": True,
        "exact_add2_float_order_repaired": True,
        "all_six_transfer_families_universal": True,
        "all_three_abstention_classes_universal": True,
        "v4_string_domain_counterexample_reproduced": v4_counterexample,
        "nonproduction_falsification": {"populations": populations, "cases": cases, "all_pass": True},
        "adversarial_str_and_bytes_subclass_dispatch": "PASS",\n        "production_or_terminal_cases_generated": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    out = ROOT / "unknown_domain_v6_total_exact_verification.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
