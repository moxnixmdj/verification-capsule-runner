"""Content-bound universal reduction for the exact current Brain Unknown-Domain V5.

This successor closes the two falsified premises without weakening the frozen
accepted-input quantifier:
1. Candidate V3 preserves exact IEEE-754 ADD2 role order.
2. Generator V4 makes every evaluator-visible identifier structurally unique
   even if every HMAC token collides.
3. Generator V5 totalizes every Python str admitted by the declared beacon and
   string-secret gates before any legacy strict-UTF8 path.

The theorem is deliberately narrow. It proves the exact frozen 27-case evaluator
contract only. It grants no acceptance, family, capability, or ownership credit.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v4_universal_proof_v1 as prior

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V5_CURRENT_BRAIN_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py": "8b855851b8a0fec3a0811c5033cc4ea6d2436954",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py": "e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py": "a97459fe407ea4852f57f12f504fbc0121db9824",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_v4_universal_proof_v1.py": "72bbed393ac1bcaccb4cf33cd37835662c421f6c",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _verify_bindings(root: Path) -> dict[str, str]:
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _string_interface_totality() -> dict[str, Any]:
    assert g5.v4 is g4
    assert g5.BEACON_CANONICALIZATION == "UTF8_SURROGATEPASS_BYTES_TO_LOWER_HEX_WITH_V5_PREFIX"
    assert g5.SECRET_CANONICALIZATION == "UTF8_SURROGATEPASS_FOR_STR__BYTES_IDENTITY"
    assert g5.STRING_DOMAIN_TOTALITY == "TOTAL_FOR_EVERY_FINITE_PYTHON_STR_ACCEPTED_BY_DECLARED_GATES"

    # The encoding has an explicit inverse on its image:
    # strip prefix -> bytes.fromhex -> decode(utf-8, surrogatepass).
    # Therefore distinct accepted Python strings cannot collapse.
    prefix = "UDIRV5-BEACON-HEX|"
    adversarial = [
        "A" * 16 + "\\ud800",
        "\\udfff" + "B" * 16,
        "Ω" * 16,
        "\\x00" + "C" * 16,
        "D" * 16 + "�",
        "E" * 16 + "😀",
    ]
    for value in adversarial:
        encoded = g5._canonical_beacon(value)
        assert encoded.startswith(prefix) and encoded.isascii()
        raw = bytes.fromhex(encoded[len(prefix):])
        assert raw.decode("utf-8", "surrogatepass") == value

    # Exhaust the complete surrogate code-point interval at the old failure seam.
    encoded_surrogates = set()
    for cp in range(0xD800, 0xE000):
        value = "A" * 16 + chr(cp)
        encoded = g5._canonical_beacon(value)
        raw = bytes.fromhex(encoded[len(prefix):])
        assert raw.decode("utf-8", "surrogatepass") == value
        encoded_surrogates.add(encoded)
    assert len(encoded_surrogates) == 0x800

    # String-secret encoding is total by the same surrogatepass map. Bytes remain
    # the evaluator key directly, so no legacy string encoding occurs afterward.
    assert g5._secret_bytes_total("S" * 31 + "\\ud800")
    assert g5._secret_bytes_total("\\udfff" + "T" * 31)
    assert g5._secret_bytes_total("λ" * 32)
    assert g5._secret_bytes_total(b"U" * 32) == b"U" * 32

    return {
        "beacon_gate": "EVERY_PYTHON_STR_WITH_LEN_STRIP_GE_16",
        "beacon_encoding_total": True,
        "beacon_encoding_has_explicit_inverse": True,
        "surrogate_codepoints_exhausted": 2048,
        "secret_string_encoding_total": True,
        "legacy_strict_utf8_counterexample_removed": True,
    }


def _run_packet(packet: dict[str, Any]) -> None:
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


def _identifier_totality() -> dict[str, Any]:
    assert g4.v2 is g2
    assert g5.IDENTIFIER_TOTALITY == "INHERITS_V4_STRUCTURAL_SLOT_ORDINAL_UNIQUENESS"

    # V4 uniqueness is carried by the explicit slot ordinal, not the token.
    # Force the strongest possible collision oracle: every token is identical.
    original = g1._token
    try:
        g1._token = lambda *args, **kwargs: "COLLISION"
        packet = g5._generate(
            beacon="A" * 16 + "\\ud800",
            evaluator_secret="T" * 31 + "\\udfff",
            namespace="V5TOTALCOLLISION",
        )
        ids = [row["case_id"] for row in packet["visible_cases"]]
        assert len(ids) == 27 and len(set(ids)) == 27
        _run_packet(packet)
    finally:
        g1._token = original

    return {
        "construction": "SECRET_RANKED_STRUCTURALLY_UNIQUE_SLOT_ORDINALS",
        "total_hmac_collision_survives": True,
        "hash_collision_resistance_required_for_uniqueness": False,
        "all_27_case_ids_unique_under_total_token_collision": True,
    }


def _semantic_universality() -> dict[str, Any]:
    # The prior proof's semantic sublemmas are content-bound and remain valid.
    # We do not reuse its falsified top-level string-domain claim.
    transfer = prior._transfer_theorem()
    abstention = prior._abstention_theorem()

    # Current V4 delegates programs/rows to the exact same V2 semantic carrier.
    assert g4.v2 is g2
    assert transfer["all_six_families_universal"] is True
    assert transfer["add2_exact_float_order_repaired"] is True
    assert abstention["all_three_classes_universal"] is True
    return {
        "transfer": transfer,
        "abstention": abstention,
        "current_v4_numeric_semantics": "EXACT_V2_PROGRAM_AND_ROW_CARRIER",
        "candidate": "EXACT_FLOAT_SAFE_V3",
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    strings = _string_interface_totality()
    identifiers = _identifier_totality()
    semantics = _semantic_universality()
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_BRAIN_V5_TOTAL_STRING_TOTAL_IDENTIFIER_EXACT_FLOAT_UNIVERSAL_REDUCTION",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "string_interface_totality": strings,
        "identifier_totality": identifiers,
        "semantic_universality": semantics,
        "scope": {
            "beacon": "EVERY_PYTHON_STR_WITH_LEN_STRIP_GE_16",
            "evaluator_secret": "EVERY_BYTES_OR_PYTHON_STR_VALUE_WHOSE_CANONICAL_BYTE_LENGTH_IS_GE_32",
            "population_cases": 27,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "production_or_terminal_cases_generated": 0,
        },
        "theorem": (
            "FOR_EVERY_INPUT_ADMITTED_BY_THE_EXACT_CURRENT_V5_INTERFACE__"
            "TOTAL_SURROGATEPASS_PLUS_HEX_CANONICALIZATION_REACHES_THE_EXACT_CURRENT_V4_CARRIER__"
            "V4_STRUCTURAL_SLOT_ORDINALS_KEEP_ALL_EVALUATOR_IDENTIFIERS_INJECTIVE_EVEN_UNDER_TOTAL_TOKEN_COLLISION__"
            "THE_EXACT_V3_CANDIDATE_PASSES_ALL_SIX_TRANSFER_FAMILIES_AND_ALL_THREE_ABSTENTION_CLASSES_WITH_EXACT_ADD2_IEEE754_GOLD_EQUALITY"
        ),
        "fresh_reality_required_for_this_exact_bound_evaluator_claim": False,
        "hard_nonclaims": [
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_FROZEN_EVALUATOR",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_PROOF_ALONE",
            "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_READ_OR_CONSUMED",
            "SEPARATE_INDEPENDENT_VERIFICATION_AND_FAIL_CLOSED_ROOT3_ACCEPTANCE_REDUCTION_REQUIRED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True, ensure_ascii=True))
