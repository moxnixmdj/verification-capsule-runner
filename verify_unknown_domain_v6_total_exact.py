# V2 frozen-gate deterministic workflow trigger: 2026-10-05
#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "unknown_domain_v6_20261005"
BRAIN_SUBJECT_REF = "486b44073e4b7250025302c55682c476a434a321"

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

class HostileStr(str):
    def strip(self, *args, **kwargs):
        raise RuntimeError("INSTANCE_STRIP_MUST_NOT_RUN")
    def encode(self, *args, **kwargs):
        raise RuntimeError("INSTANCE_ENCODE_MUST_NOT_RUN")
    def __str__(self):
        raise RuntimeError("INSTANCE_STR_MUST_NOT_RUN")
    def __len__(self):
        raise RuntimeError("INSTANCE_LEN_MUST_NOT_RUN")
    def __getattribute__(self, name):
        raise RuntimeError("INSTANCE_GETATTRIBUTE_MUST_NOT_RUN:" + name)

class HostileBytes(bytes):
    def __bytes__(self):
        raise RuntimeError("INSTANCE_BYTES_MUST_NOT_RUN")
    def __len__(self):
        raise RuntimeError("INSTANCE_LEN_MUST_NOT_RUN")
    def __getitem__(self, key):
        raise RuntimeError("INSTANCE_GETITEM_MUST_NOT_RUN")
    def __iter__(self):
        raise RuntimeError("INSTANCE_ITER_MUST_NOT_RUN")
    def __buffer__(self, flags):
        raise RuntimeError("INSTANCE_BUFFER_MUST_NOT_RUN")
    def __release_buffer__(self, view):
        raise RuntimeError("INSTANCE_RELEASE_BUFFER_MUST_NOT_RUN")

def exact_run(packet, c3, harness, scorer):
    rows = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        out = harness.execute_case(
            candidate_step=c3.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"] is True, (visible["case_id"], out)
        rows.append(out["scorer_result"])
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
    return len(rows)

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
    assert result["string_interface_totality"]["isinstance_accepted_subclass_override_hooks_bypassed"] is True
    assert result["identifier_totality_proof"]["forced_total_token_collision_survives_construction"] is True
    assert result["transfer_proof"]["all_six_families_universal"] is True
    assert result["transfer_proof"]["add2_exact_float_order_repaired"] is True
    assert result["abstention_proof"]["all_three_classes_universal"] is True

    # Reproduce the exact pre-repair defect class first.
    old_style = HostileStr("A" * 16 + "\ud800")
    try:
        old_style.strip()
    except RuntimeError:
        old_instance_strip_fails = True
    else:
        raise AssertionError("HOSTILE_INSTANCE_STRIP_DID_NOT_FAIL")
    assert str.strip(old_style) == ("A" * 16 + "\ud800")
    try:
        old_style.encode("utf-8", "surrogatepass")
    except RuntimeError:
        old_instance_encode_fails = True
    else:
        raise AssertionError("HOSTILE_INSTANCE_ENCODE_DID_NOT_FAIL")
    assert str.encode(old_style, "utf-8", "surrogatepass").endswith(b"\xed\xa0\x80")

    # The repaired gate/canonicalizer must bypass all Python-level overrides.
    assert g5._beacon_gate(old_style) is old_style
    canonical = g5._canonical_beacon(old_style)
    assert canonical.startswith("UDIRV5-BEACON-HEX|")
    assert canonical.isascii()

    hostile_secret_text = HostileStr("S" * 31 + "\udfff")
    text_bytes = g5._secret_bytes_total(hostile_secret_text)
    assert isinstance(text_bytes, bytes) and len(text_bytes) >= 32

    hostile_secret_bytes = HostileBytes(b"B" * 32)
    try:
        memoryview(hostile_secret_bytes).tobytes()
    except RuntimeError as exc:
        assert "BUFFER" in str(exc)
        old_buffer_dispatch_failure_reproduced = True
    else:
        raise AssertionError("PYTHON312_BUFFER_OVERRIDE_COUNTEREXAMPLE_NOT_REPRODUCED")
    raw_bytes = g5._secret_bytes_total(hostile_secret_bytes)
    assert type(raw_bytes) is bytes and raw_bytes == b"B" * 32
    assert bytes.__getitem__(hostile_secret_bytes, slice(None)) == b"B" * 32

    # A subclass shorter than the public gate must still reject deterministically
    # without invoking its hostile instance methods.
    try:
        g5._beacon_gate(HostileStr("short"))
    except Exception as exc:
        assert exc.__class__.__name__ == "UnknownDomainGeneratorError"
    else:
        raise AssertionError("SHORT_HOSTILE_SUBCLASS_MUST_REJECT")

    # Exact non-production population on the formerly falsifying subclass.
    subclass_cases = 0
    subclass_cases += exact_run(
        g5._generate(
            beacon=old_style,
            evaluator_secret=hostile_secret_text,
            namespace="VERIFY-SUBCLASS-TEXT",
        ),
        c3, harness, scorer,
    )
    subclass_cases += exact_run(
        g5._generate(
            beacon=HostileStr("\udfff" + "B" * 16),
            evaluator_secret=hostile_secret_bytes,
            namespace="VERIFY-SUBCLASS-BYTES",
        ),
        c3, harness, scorer,
    )
    assert subclass_cases == 54

    # Preserve prior exact counterexample and finite falsification coverage.
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
            cases += exact_run(packet, c3, harness, scorer)
            populations += 1
    assert populations == 16
    assert cases == 432

    receipt = {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__INDEPENDENT_CONTENT_BOUND_REPAIRED_SUBCLASS_TOTALITY_AND_27_CASE_EXECUTION__ZERO_CREDIT",
        "brain_subject_ref": BRAIN_SUBJECT_REF,
        "subject_blobs": observed,
        "universal_theorem_status": result["status"],
        "surrogate_codepoints_exhausted": 2048,
        "isinstance_str_subclass_override_hooks_bypassed": True,
        "isinstance_bytes_subclass_override_hooks_bypassed": True,
        "python312_buffer_hook_adversary_included": True,
        "old_instance_strip_failure_reproduced": old_instance_strip_fails,
        "old_instance_encode_failure_reproduced": old_instance_encode_fails,
        "old_python312_buffer_dispatch_failure_reproduced": old_buffer_dispatch_failure_reproduced,
        "str_subclass_override_getattribute_attacked": True,
        "str_subclass_override_len_attacked": True,
        "bytes_subclass_override_bytes_attacked": True,
        "bytes_subclass_override_buffer_attacked": True,
        "bytes_subclass_override_len_attacked": True,
        "bytes_subclass_override_getitem_attacked": True,
        "bytes_subclass_override_iter_attacked": True,
        "base_bytes_getitem_full_slice_bypass_verified": True,
        "hostile_subclass_exact_scorer_cases": subclass_cases,
        "structural_identifier_totality": True,
        "exact_add2_float_order_repaired": True,
        "all_six_transfer_families_universal": True,
        "all_three_abstention_classes_universal": True,
        "v4_string_domain_counterexample_reproduced": v4_counterexample,
        "ordinary_nonproduction_falsification": {
            "populations": populations,
            "cases": cases,
            "all_pass": True,
        },
        "total_exact_scorer_cases": cases + subclass_cases,
        "production_or_terminal_cases_generated": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "NO_ACCEPTANCE_PROMOTION_FROM_THIS_VERIFIER_BY_ITSELF",
            "NO_OPEN_WORLD_GENERALIZATION_BEYOND_THE_BOUND_EVALUATOR_CONTRACT",
            "SEPARATE_FAIL_CLOSED_ACCEPTANCE_REDUCTION_REQUIRED",
        ],
    }
    out = ROOT / "unknown_domain_v6_total_exact_verification.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
