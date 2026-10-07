from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from canonical.runtime.opus55_opaque_state_observational_quotient_v1 import (
    verify_observational_equivalence,
)

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/governance/OPUS55_OPAQUE_STATE_OBSERVATIONAL_QUOTIENT_20261005_V1.json":
        "91c19b54193bd3d22e54f5bc26ae3abd819ef892",
    "canonical/runtime/opus55_opaque_state_observational_quotient_v1.py":
        "4d99d262efd20501428160c3f2f03e92348ed03d",
    "canonical/tests/test_opus55_opaque_state_observational_quotient_v1.py":
        "9cfafc353c16aaf638f871e1c7e14bfb60082c84",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def base(ids=("A", "B", "C")):
    a, b, c = ids
    return [
        {"type": "TEXT", "actor": "USER", "payload": "goal"},
        {"type": "OPAQUE_STATE_EMIT", "actor": "OPUS55_MODEL_POLICY",
         "carrier_kind": "THINKING_SIGNATURE", "carrier_id": a},
        {"type": "OPAQUE_STATE_EMIT", "actor": "OPUS55_MODEL_POLICY",
         "carrier_kind": "THINKING_SIGNATURE", "carrier_id": b},
        {"type": "OPAQUE_STATE_ECHO", "actor": "OPUS55_MODEL_POLICY",
         "carrier_kind": "THINKING_SIGNATURE", "carrier_id": a},
        {"type": "TOOL_USE", "actor": "OPUS55_MODEL_POLICY",
         "payload": {"name": "search", "query": "q"}},
        {"type": "OPAQUE_STATE_EMIT", "actor": "OPUS55_MODEL_POLICY",
         "carrier_kind": "REDACTED_THINKING", "carrier_id": c},
        {"type": "OPAQUE_STATE_ECHO", "actor": "OPUS55_MODEL_POLICY",
         "carrier_kind": "THINKING_SIGNATURE", "carrier_id": b},
        {"type": "TEXT", "actor": "OPUS55_MODEL_POLICY", "payload": "answer"},
    ]


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def main():
    # Exact content-addressed subject.
    for rel, want in EXPECTED.items():
        data = (ROOT / rel).read_bytes()
        got = git_blob_sha(data)
        require(got == want, f"blob mismatch {rel}: {got} != {want}")

    gov = json.loads(
        (ROOT / "canonical/governance/OPUS55_OPAQUE_STATE_OBSERVATIONAL_QUOTIENT_20261005_V1.json").read_text()
    )

    # Governance boundary must remain zero-credit and fail closed.
    require(gov["independent_verification_required"] is True, "independent verification weakened")
    for key in ("scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"):
        require(gov[key] is False, f"{key} unexpectedly true")
    for key in ("acceptance_credit_delta", "family_credit_delta", "capability_credit_delta", "ownership_credit_delta"):
        require(gov["accounting"][key] == 0, f"{key} nonzero")
    require(gov["accounting"]["new_reality_units_consumed"] == 0, "fresh reality consumed")
    require(
        "DOES_NOT_SELF_CERTIFY_SEMANTIC_OPACITY_OR_BRAIN_STATE_TRANSITION_DOMINANCE"
        in gov["implementation"]["runtime_scope"],
        "runtime scope overclaims semantics",
    )
    require(
        "NO_CLAIM_RAW_VENDOR_BYTES_ARE_ALWAYS_IRRELEVANT" in gov["hard_nonclaims"],
        "missing raw-byte relevance falsifier boundary",
    )

    canonical = base()

    # Independent exhaustive alpha-renaming check for three carrier values.
    names = ("X", "Y", "Z")
    checked = 0
    for perm in itertools.permutations(names):
        verdict = verify_observational_equivalence(canonical, base(perm))
        require(verdict["status"] == "EQUIVALENT", f"bijection rejected: {perm}: {verdict}")
        checked += 1
    require(checked == 6, "permutation coverage wrong")

    # Non-alpha differences must survive.
    actor_mut = base(("X", "Y", "Z"))
    actor_mut[1]["actor"] = "SERVER_EXECUTOR"
    require(
        verify_observational_equivalence(canonical, actor_mut)["status"] == "NOT_EQUIVALENT",
        "actor mutation erased",
    )

    semantic_mut = base(("X", "Y", "Z"))
    semantic_mut[-1]["payload"] = "different"
    require(
        verify_observational_equivalence(canonical, semantic_mut)["status"] == "NOT_EQUIVALENT",
        "semantic mutation erased",
    )

    kind_mut = base(("X", "Y", "Z"))
    kind_mut[1]["carrier_kind"] = "REDACTED_THINKING"
    require(
        verify_observational_equivalence(canonical, kind_mut)["status"] == "NOT_EQUIVALENT",
        "carrier-kind mutation erased",
    )

    order_mut = base(("X", "Y", "Z"))
    order_mut[1], order_mut[2] = order_mut[2], order_mut[1]
    require(
        verify_observational_equivalence(canonical, order_mut)["status"] == "NOT_EQUIVALENT",
        "carrier order mutation erased",
    )

    link_mut = base(("X", "Y", "Z"))
    link_mut[3]["carrier_id"] = "Y"
    require(
        verify_observational_equivalence(canonical, link_mut)["status"] == "NOT_EQUIVALENT",
        "emit/echo linkage mutation erased",
    )

    missing_actor = [{"type": "TEXT", "payload": "x"}]
    verdict = verify_observational_equivalence(missing_actor, missing_actor)
    require(verdict["status"] == "FAIL_CLOSED", "missing actor did not fail closed")

    # Distinct raw values cannot collapse into one emitted identity.
    collapse = base(("SAME", "SAME", "Z"))
    verdict = verify_observational_equivalence(canonical, collapse)
    require(verdict["status"] == "FAIL_CLOSED", "non-bijective carrier collapse accepted")

    print(json.dumps({
        "status": "PASS",
        "brain_pr": 2181,
        "brain_head": "31564e99c65e199824b137f0a4e772e736e531f9",
        "exact_blobs": EXPECTED,
        "independent_alpha_bijections_checked": checked,
        "adversarial_dimensions": [
            "actor", "semantic_payload", "carrier_kind", "event_order",
            "emit_echo_linkage", "missing_actor", "non_bijective_collapse"
        ],
        "semantic_opacity_proved": False,
        "brain_transition_dominance_proved": False,
        "acceptance_credit_delta": 0,
        "terminal_completion": False,
    }, indent=2))


if __name__ == "__main__":
    main()
