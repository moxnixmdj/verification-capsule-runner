#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v7_genuine_type_proof_v1 as proof

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("unknown_domain_v7_genuine_type_receipt.json")

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py": "e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py": "d2f529ed9a006f53e75d06ece6f2acb54211b127",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/tests/test_unknown_domain_direct_v5.py": "5b1dc24c7ec65edc32475917349c5d8725b9a655",
    "canonical/runtime/unknown_domain_direct_v7_genuine_type_proof_v1.py": "3d7171b34a19f2600f9c5bb512d116806deba481",
}

FROZEN_SEMANTICS = {
    "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json": "fd586455d582c38c7062ffe735f86cb9f2e803ab",
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json": "52090daf78d12020af48c1b6ffaea056d9029e1b",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def run_packet(packet) -> int:
    assert packet["case_count"] == 27
    rows = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        out = harness.execute_case(
            candidate_step=c3.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"] is True, (visible["case_id"], out["scorer_result"])
        rows.append(out["scorer_result"])
    agg = scorer.aggregate(rows)
    assert agg["all_27_cases_pass"] is True
    return 27

class HostileStr(str):
    def __getattribute__(self, name):
        if name in {"strip", "encode"}:
            raise RuntimeError("HOSTILE_STR_GETATTRIBUTE_" + name)
        return str.__getattribute__(self, name)

    def strip(self, *args, **kwargs):
        raise RuntimeError("HOSTILE_STR_STRIP")

    def encode(self, *args, **kwargs):
        raise RuntimeError("HOSTILE_STR_ENCODE")

    def __len__(self):
        raise RuntimeError("HOSTILE_STR_LEN")

class HostileBytes(bytes):
    def __bytes__(self):
        raise RuntimeError("HOSTILE_BYTES_BYTES")

    def __buffer__(self, *args, **kwargs):
        raise RuntimeError("HOSTILE_BYTES_BUFFER")

    def __len__(self):
        raise RuntimeError("HOSTILE_BYTES_LEN")

    def __getitem__(self, *args, **kwargs):
        raise RuntimeError("HOSTILE_BYTES_GETITEM")

    def __iter__(self):
        raise RuntimeError("HOSTILE_BYTES_ITER")

class FakeStr:
    @property
    def __class__(self):
        return str

class FakeBytes:
    @property
    def __class__(self):
        return bytes

# Exact subject and frozen semantic byte bindings.
got = {path: git_blob_sha(ROOT / path) for path in EXPECTED}
assert got == EXPECTED, {"expected": EXPECTED, "got": got}
frozen_got = {path: git_blob_sha(ROOT / path) for path in FROZEN_SEMANTICS}
assert frozen_got == FROZEN_SEMANTICS, {"expected": FROZEN_SEMANTICS, "got": frozen_got}

# Reproduce the class-spoof property that invalidated isinstance as a universal gate.
fake_str = FakeStr()
fake_bytes = FakeBytes()
assert isinstance(fake_str, str) is True
assert isinstance(fake_bytes, bytes) is True
assert issubclass(type(fake_str), str) is False
assert issubclass(type(fake_bytes), bytes) is False

rejected = {}
for name, fn, arg, expected_error in (
    ("fake_str_beacon", g5._beacon_gate, fake_str, "POST_FREEZE_BEACON_INVALID"),
    ("fake_str_secret", g5._secret_bytes_total, fake_str, "EVALUATOR_SECRET_INVALID"),
    ("fake_bytes_secret", g5._secret_bytes_total, fake_bytes, "EVALUATOR_SECRET_INVALID"),
):
    try:
        fn(arg)
    except g1.UnknownDomainGeneratorError as exc:
        assert str(exc) == expected_error, (name, str(exc))
        rejected[name] = True
    else:
        raise AssertionError(name + "_WAS_ADMITTED")

# Genuine subclasses remain supported even when their Python-level hooks are hostile.
hostile_beacon = HostileStr("A" * 16 + "\ud800")
hostile_str_secret = HostileStr("S" * 31 + "\udfff")
hostile_bytes_secret = HostileBytes(b"B" * 32)

canon = g5._canonical_beacon(hostile_beacon)
assert canon.isascii()
assert canon == "UDIRV5-BEACON-HEX|" + ("A" * 16 + "\ud800").encode("utf-8", "surrogatepass").hex()

str_secret = g5._secret_bytes_total(hostile_str_secret)
assert type(str_secret) is bytes
assert str_secret == ("S" * 31 + "\udfff").encode("utf-8", "surrogatepass")

bytes_secret = g5._secret_bytes_total(hostile_bytes_secret)
assert type(bytes_secret) is bytes
assert bytes_secret == b"B" * 32

# Exhaust the historically dangerous surrogate interval through the hostile subclass seam.
surrogates = set()
for cp in range(0xD800, 0xE000):
    value = HostileStr("A" * 16 + chr(cp))
    encoded = g5._canonical_beacon(value)
    assert encoded.isascii()
    surrogates.add(encoded)
assert len(surrogates) == 0x800

# Execute exact hidden scorer/harness path on both hostile secret representations.
case_executions = 0
case_executions += run_packet(g5._generate(
    beacon=hostile_beacon,
    evaluator_secret=hostile_str_secret,
    namespace="V7-HOSTILE-STR",
))
case_executions += run_packet(g5._generate(
    beacon=hostile_beacon,
    evaluator_secret=hostile_bytes_secret,
    namespace="V7-HOSTILE-BYTES",
))

# Force every legacy token to collide and require structural IDs + full scorer path to survive.
old_token = g1._token
try:
    g1._token = lambda *args, **kwargs: "COLLISION"
    collided = g5._generate(
        beacon=hostile_beacon,
        evaluator_secret=hostile_bytes_secret,
        namespace="V7-COLLISION",
    )
    assert len({x["case_id"] for x in collided["visible_cases"]}) == 27
    case_executions += run_packet(collided)
finally:
    g1._token = old_token

assert case_executions == 81

# Execute the content-bound V7 theorem only after the independent attacks pass.
theorem = proof.prove(ROOT)
required_status = "PASS__GENUINE_RUNTIME_TYPE_DOMAIN_TOTALITY_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert theorem["status"] == required_status
totality = theorem["string_interface_totality"]
assert totality["genuine_runtime_subclass_override_hooks_bypassed"] is True
assert totality["bytes_subclass_buffer_protocol_override_bypassed"] is True
assert totality["class_spoof_proxies_rejected_by_real_type_gate"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"] == 0
assert theorem["accounting"]["acceptance_credit_delta"] == 0

receipt = {
    "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V7_GENUINE_TYPE_INDEPENDENT_VERIFICATION_V1",
    "status": "PASS__INDEPENDENT_CONTENT_BOUND_GENUINE_TYPE_TOTALITY_AND_CLASS_SPOOF_REJECTION__ZERO_CREDIT",
    "python": platform.python_version(),
    "exact_subject_blobs": EXPECTED,
    "frozen_semantic_blobs": FROZEN_SEMANTICS,
    "attacks": {
        "fake_str_isinstance_spoof_reproduced": True,
        "fake_bytes_isinstance_spoof_reproduced": True,
        "fake_str_beacon_rejected_before_descriptor_use": rejected["fake_str_beacon"],
        "fake_str_secret_rejected_before_descriptor_use": rejected["fake_str_secret"],
        "fake_bytes_secret_rejected_before_descriptor_use": rejected["fake_bytes_secret"],
        "genuine_hostile_str_subclass_passed": True,
        "genuine_hostile_bytes_subclass_passed": True,
        "surrogate_codepoints_exhausted": 0x800,
        "forced_total_token_collision_rechecked": True,
        "adversarial_exact_case_executions": case_executions,
    },
    "v7_proof_status": theorem["status"],
    "production_or_terminal_cases_generated_read_or_consumed": 0,
    "acceptance_credit_delta": 0,
    "family_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
    "hard_nonclaims": [
        "THIS_RECEIPT_DOES_NOT_SELF_PROMOTE_THE_BRAIN_PREDICATE",
        "SEPARATE_FAIL_CLOSED_ROOT3_REPROMOTION_REDUCTION_REMAINS_REQUIRED",
    ],
}

OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True, ensure_ascii=True))
