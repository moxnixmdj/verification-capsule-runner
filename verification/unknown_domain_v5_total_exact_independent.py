#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v5_total_exact_universal_proof_v1 as proposed

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py": "e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py": "a97459fe407ea4852f57f12f504fbc0121db9824",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_v4_universal_proof_v1.py": "72bbed393ac1bcaccb4cf33cd37835662c421f6c",
    "canonical/runtime/unknown_domain_direct_v5_total_exact_universal_proof_v1.py": "a71a2efffe0aafe3dbbe27d66b6a338563ed368c",
}


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


actual = {p: blob(ROOT / p) for p in EXPECTED}
assert actual == EXPECTED, {"expected": EXPECTED, "actual": actual}

# 1. Reproduce the exact accepted-string failure in V4.
bad_beacon = "A" * 16 + "\ud800"
assert len(bad_beacon.strip()) >= 16
failed = False
try:
    g4._generate(
        beacon=bad_beacon,
        evaluator_secret=b"S" * 32,
        namespace="V4-STRING-FALSIFIER",
    )
except UnicodeEncodeError:
    failed = True
assert failed

# 2. Exhaust the complete surrogate range through V5.
surrogate_outputs = {
    g5._canonical_beacon("A" * 16 + chr(cp))
    for cp in range(0xD800, 0xE000)
}
assert len(surrogate_outputs) == 2048
assert all(x.isascii() for x in surrogate_outputs)

# 3. Independently inspect the exact V4 structural-label mechanism.
source = inspect.getsource(g4._ranked_labels)
assert "len(ks) != len(set(ks))" in source
assert "for slot, (_, key) in enumerate(ranked)" in source
assert 'f"{prefix}{slot}_{suffix}"' in source
assert g4.v2 is g2

for n in range(1, 28):
    keys = [f"k{i}" for i in range(n)]
    labels = g4._ranked_labels(
        b"Q" * 32,
        "STRUCTURAL-CHECK-000000000",
        scope=f"n={n}",
        keys=keys,
        prefix="L-",
    )
    assert set(labels) == set(keys)
    assert len(set(labels.values())) == n

# 4. Reproduce a V2 exact-float failure on the V5-composed generator and require
# V3 to repair the identical case.
counterexample = None
for k in range(1024):
    packet = g5._generate(
        beacon=f"V5-FLOAT-{k:04d}-BEACON",
        evaluator_secret=hashlib.sha256(f"float-{k}".encode()).digest(),
        namespace=f"V5FLOAT{k}",
    )
    for index in (4, 10):
        visible = packet["visible_cases"][index]
        hidden = packet["hidden_records"][index]
        bad = harness.execute_case(
            candidate_step=c2.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        if (
            not bad["scorer_result"]["pass"]
            and "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"]["errors"]
        ):
            good = harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            assert good["scorer_result"]["pass"] is True
            assert (
                good["candidate_terminal_action"]["terminal_consequence"]
                == hidden["gold_terminal_consequence"]
            )
            counterexample = {
                "seed": k,
                "index": index,
                "v2_terminal": bad["candidate_terminal_action"]["terminal_consequence"],
                "gold": hidden["gold_terminal_consequence"],
                "v3_probe_count": good["probe_count"],
            }
            break
    if counterexample is not None:
        break
assert counterexample is not None

# 5. Adversarial string-interface matrix through the full V5 27-case path.
beacons = [
    "A" * 16 + "\ud800",
    "\udfff" + "B" * 16,
    "Ω" * 16,
    "\x00" + "C" * 16,
]
values = [
    b"S" * 32,
    "T" * 31 + "\ud800",
    "\udfff" + "U" * 31,
    "λ" * 32,
]
adversarial_cases = 0
for i, beacon in enumerate(beacons):
    for j, value in enumerate(values):
        packet = g5._generate(
            beacon=beacon,
            evaluator_secret=value,
            namespace=f"V5EDGE{i}{j}",
        )
        rows = []
        assert packet["case_count"] == 27
        for visible, hidden in zip(
            packet["visible_cases"], packet["hidden_records"], strict=True
        ):
            out = harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            assert out["scorer_result"]["pass"] is True, out["scorer_result"]
            rows.append(out["scorer_result"])
            adversarial_cases += 1
        assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert adversarial_cases == 432

# 6. Broad deterministic nonproduction sweep through the exact V5 composition.
populations = 256
ordinary_cases = 0
for k in range(populations):
    packet = g5._generate(
        beacon="V5-INDEPENDENT-" + hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24],
        evaluator_secret=hashlib.sha256(f"value-{k}".encode()).digest(),
        namespace=f"V5I{k}",
    )
    rows = []
    for visible, hidden in zip(
        packet["visible_cases"], packet["hidden_records"], strict=True
    ):
        out = harness.execute_case(
            candidate_step=c3.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"] is True, out["scorer_result"]
        rows.append(out["scorer_result"])
        ordinary_cases += 1
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert ordinary_cases == 6912

# 7. Compare the frozen theorem only after independent attacks.
theorem = proposed.prove(ROOT)
assert theorem["status"] == "PASS__V5_TOTAL_STRING_STRUCTURAL_IDS_EXACT_FLOAT_UNIVERSAL_COMPOSITION"
assert theorem["string_interface_totality"]["surrogate_codepoints_exhausted"] == 2048
assert theorem["composition_proof"]["all_six_transfer_families_universal"] is True
assert theorem["composition_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["composition_proof"]["all_three_abstention_classes_universal"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"] == 0
assert theorem["accounting"]["acceptance_credit_delta"] == 0

receipt = {
    "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V5_TOTAL_EXACT_INDEPENDENT_VERIFICATION_V1",
    "status": "PASS__INDEPENDENT_V5_TOTAL_STRING_STRUCTURAL_ID_EXACT_FLOAT_COMPOSITION",
    "exact_subject_blobs": EXPECTED,
    "prior_v4_string_failure_reproduced": True,
    "surrogate_codepoints_exhausted": 2048,
    "v2_exact_float_counterexample": counterexample,
    "nonproduction_falsification": {
        "ordinary_populations": populations,
        "ordinary_cases": ordinary_cases,
        "adversarial_string_cases": adversarial_cases,
        "total_scored_cases": ordinary_cases + adversarial_cases,
        "all_pass": True,
    },
    "production_or_terminal_cases_generated": 0,
    "acceptance_credit_delta": 0,
}
Path("unknown_domain_v5_total_exact_receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
