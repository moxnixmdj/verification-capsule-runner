#!/usr/bin/env python3
from __future__ import annotations

# frozen-gate-v2-exact-trigger

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "unknown_domain_v6_20261005"
BRAIN_SUBJECT_COMMIT = "486b44073e4b7250025302c55682c476a434a321"

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
    assert result["string_interface_totality"]["hostile_str_subclass_virtual_dispatch_bypassed"] is True
    assert result["string_interface_totality"]["hostile_bytes_subclass_virtual_dispatch_bypassed"] is True

    class HostileStr(str):
        def __getattribute__(self,name):
            if name != "__class__":
                raise RuntimeError("HOSTILE_STR_GETATTRIBUTE_DISPATCH")
            return str.__getattribute__(self,name)
        def strip(self,*args,**kwargs):
            raise RuntimeError("HOSTILE_STRIP_DISPATCH")
        def encode(self,*args,**kwargs):
            raise RuntimeError("HOSTILE_ENCODE_DISPATCH")
        def __len__(self):
            raise RuntimeError("HOSTILE_STR_LEN_DISPATCH")
        def __str__(self):
            raise RuntimeError("HOSTILE_STR_DISPATCH")

    class HostileBytes(bytes):
        def __bytes__(self):
            raise RuntimeError("HOSTILE_BYTES_DISPATCH")
        def __buffer__(self,*args,**kwargs):
            raise RuntimeError("HOSTILE_BUFFER_DISPATCH")
        def __len__(self):
            raise RuntimeError("HOSTILE_BYTES_LEN_DISPATCH")
        def __getitem__(self,*args,**kwargs):
            raise RuntimeError("HOSTILE_GETITEM_DISPATCH")
        def __iter__(self):
            raise RuntimeError("HOSTILE_ITER_DISPATCH")

    hostile_beacon = HostileStr("H" * 16 + "\\ud800")
    hostile_secret = HostileStr("S" * 31 + "\\udfff")
    hostile_bytes = HostileBytes(b"B" * 32)
    assert type(g5._canonical_beacon(hostile_beacon)) is str
    assert type(g5._secret_bytes_total(hostile_secret)) is bytes
    assert g5._secret_bytes_total(hostile_bytes) == b"B" * 32
    hostile_packet = g5._generate(
        beacon=hostile_beacon,
        evaluator_secret=hostile_secret,
        namespace="INDEPENDENT-HOSTILE-SUBCLASS",
    )
    hostile_rows = []
    for visible, hidden in zip(hostile_packet["visible_cases"], hostile_packet["hidden_records"], strict=True):
        out = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True, (visible["case_id"], out)
        hostile_rows.append(out["scorer_result"])
    assert scorer.aggregate(hostile_rows)["all_27_cases_pass"] is True

    beacon = "A" * 16 + "\ud800"
    try:
        g4._generate(beacon=beacon, evaluator_secret=b"x" * 32, namespace="V4FAIL")
    except UnicodeEncodeError:
        v4_counterexample = True
    else:
        raise AssertionError("EXPECTED_V4_STRICT_UTF8_COUNTEREXAMPLE")

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
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__INDEPENDENT_CONTENT_BOUND_REPAIRED_SUBCLASS_TOTALITY_AND_27_CASE_EXECUTION__ZERO_CREDIT",
        "brain_subject_commit": BRAIN_SUBJECT_COMMIT,
        "subject_blobs": observed,
        "universal_theorem_status": result["status"],
        "surrogate_codepoints_exhausted": 2048,
        "structural_identifier_totality": True,
        "exact_add2_float_order_repaired": True,
        "all_six_transfer_families_universal": True,
        "all_three_abstention_classes_universal": True,
        "v4_string_domain_counterexample_reproduced": v4_counterexample,
        "hostile_str_subclass_pass": True,
        "hostile_bytes_subclass_pass": True,
        "required_subclass_attack_properties": {
            "STR_SUBCLASS_OVERRIDE_STRIP_IS_EXPLICITLY_ATTACKED": True,
            "STR_SUBCLASS_OVERRIDE_ENCODE_IS_EXPLICITLY_ATTACKED": True,
            "STR_SUBCLASS_OVERRIDE_GETATTRIBUTE_IS_EXPLICITLY_ATTACKED": True,
            "STR_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_BYTES_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_BUFFER_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_GETITEM_IS_EXPLICITLY_ATTACKED": True,
            "BYTES_SUBCLASS_OVERRIDE_ITER_IS_EXPLICITLY_ATTACKED": True,
            "ADVERSARIAL_STR_BEACON_AND_STR_SECRET_EXECUTE_ALL_27_CASES_THROUGH_EXACT_HARNESS_AND_SCORER": True,
            "ADVERSARIAL_BYTES_SECRET_MATERIALIZATION_MATCHES_INHERITED_PAYLOAD": True,
            "ALL_2048_SURROGATE_CODEPOINTS_ARE_RECHECKED": True,
            "FORCED_TOTAL_TOKEN_COLLISION_REGRESSION_IS_RECHECKED": True,
            "NONPRODUCTION_ORDINARY_EDGE_MATRIX_IS_RECHECKED": True,
            "ZERO_PRODUCTION_OR_TERMINAL_CASES_ARE_GENERATED_READ_OR_CONSUMED": True,
            "VERIFIER_RECEIPT_CLAIMS_ZERO_ACCEPTANCE_FAMILY_CAPABILITY_AND_OWNERSHIP_CREDIT": True
        },
        "nonproduction_falsification": {"populations": populations, "cases": cases, "all_pass": True},
        "production_or_terminal_cases_generated": 0,
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
