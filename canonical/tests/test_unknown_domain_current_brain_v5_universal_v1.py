from __future__ import annotations

import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v5_current_brain_universal_proof_v1 as proof


def _run(packet):
    rows = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        out = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True, out
        rows.append(out["scorer_result"])
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True


def test_exact_current_brain_v5_content_bound_universal_reduction():
    out = proof.prove()
    assert out["status"] == "PASS__CURRENT_BRAIN_V5_TOTAL_STRING_TOTAL_IDENTIFIER_EXACT_FLOAT_UNIVERSAL_REDUCTION"
    assert out["string_interface_totality"]["surrogate_codepoints_exhausted"] == 2048
    assert out["identifier_totality"]["total_hmac_collision_survives"] is True
    assert out["semantic_universality"]["transfer"]["add2_exact_float_order_repaired"] is True
    assert out["scope"]["production_or_terminal_cases_generated"] == 0


def test_old_v4_unicode_counterexample_still_reproduces_and_v5_closes_it():
    beacon = "A" * 16 + "\ud800"
    try:
        g4._generate(beacon=beacon, evaluator_secret=b"S" * 32, namespace="V4FAIL")
    except UnicodeEncodeError:
        pass
    else:
        raise AssertionError("EXPECTED_CURRENT_V4_STRICT_UTF8_COUNTEREXAMPLE")
    _run(g5._generate(beacon=beacon, evaluator_secret=b"S" * 32, namespace="V5PASS"))


def test_all_surrogate_codepoints_have_distinct_roundtripping_canonical_beacons():
    prefix = "UDIRV5-BEACON-HEX|"
    seen = set()
    for cp in range(0xD800, 0xE000):
        value = "A" * 16 + chr(cp)
        encoded = g5._canonical_beacon(value)
        assert encoded.startswith(prefix)
        assert bytes.fromhex(encoded[len(prefix):]).decode("utf-8", "surrogatepass") == value
        seen.add(encoded)
    assert len(seen) == 2048


def test_total_token_collision_does_not_break_identifier_or_case_totality():
    original = g1._token
    try:
        g1._token = lambda *args, **kwargs: "COLLISION"
        packet = g5._generate(
            beacon="A" * 16 + "\ud800",
            evaluator_secret="T" * 31 + "\udfff",
            namespace="V5COLLIDE",
        )
        assert len({row["case_id"] for row in packet["visible_cases"]}) == 27
        _run(packet)
    finally:
        g1._token = original


def test_128_nonproduction_populations_pass_end_to_end():
    for k in range(128):
        secret = hashlib.sha256(f"current-v5-secret-{k}".encode()).digest()
        beacon = "CURRENT-V5-" + hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:32]
        _run(g5._generate(beacon=beacon, evaluator_secret=secret, namespace=f"CV5{k}"))
