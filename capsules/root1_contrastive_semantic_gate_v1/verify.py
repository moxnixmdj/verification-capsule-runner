from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import root1_contrastive_semantic_gate_v1 as gate

EXPECTED_BRAIN_BLOB_SHA = "3737642f47b21b23d2892bd1ba14dbd6776ca256"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    framed = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    return hashlib.sha1(framed).hexdigest()


source_path = HERE / "root1_contrastive_semantic_gate_v1.py"
actual_blob = git_blob_sha(source_path)
assert actual_blob == EXPECTED_BRAIN_BLOB_SHA, (actual_blob, EXPECTED_BRAIN_BLOB_SHA)

GOOD = {
    "PARA_A": "Before sunrise Tuesday, Neris brought seven amber parcels to Corin.",
    "PARA_B": "After sunset Wednesday, Neris brought nine blue parcels to Corin.",
    "SIMPLE_A": "Yusuf shut Pump 3 as the eastern valve hit 82 degrees, before moving 45 liters to Tank B.",
    "SIMPLE_B": "Yusuf opened Pump 3 after the western valve fell below 18 degrees, moving 15 liters from Tank B.",
    "SUM_A": "Train 8, delayed 35 minutes outside Luxor, had two signal boxes inspected with no damage and reached Aswan at 21:10.",
    "SUM_B": "Train 8 stopped 50 minutes near Edfu, where three signal boxes showed damage, then returned to Luxor at 22:40.",
    "STORY_A": "ORION-7 found BRASS-KEY at GATE-2. It crossed HARBOR-9 carrying the key safely. ORION-7 returned BRASS-KEY to MIRA-1.",
    "STORY_B": "ORION-7 found SILVER-RING at GATE-2. It crossed TUNNEL-4 while protecting the ring. ORION-7 gave SILVER-RING to MIRA-1.",
}

positive = gate.evaluate_suite(GOOD)
assert positive["pass"], positive
assert positive["case_pass_count"] == 8, positive
assert all(positive["pair_distinction_checks"].values()), positive
assert all(positive["effect_pass"].values()), positive

fact_flip = copy.deepcopy(GOOD)
fact_flip["SIMPLE_A"] = (
    "Yusuf opened Pump 3 after the western valve fell below 18 degrees, "
    "moving 15 liters from Tank B."
)
flip_result = gate.evaluate_suite(fact_flip)
assert not flip_result["pass"], flip_result
flip_row = next(x for x in flip_result["results"] if x["probe_id"] == "SIMPLE_A")
assert not flip_row["checks"]["required_semantic_facts"], flip_row
assert not flip_row["checks"]["counterfactual_facts_absent"], flip_row

copy_case = copy.deepcopy(GOOD)
para_probe = next(x for x in gate.frozen_probes() if x.probe_id == "PARA_A")
copy_case["PARA_A"] = para_probe.source
copy_result = gate.evaluate_suite(copy_case)
copy_row = next(x for x in copy_result["results"] if x["probe_id"] == "PARA_A")
assert not copy_row["pass"], copy_row
assert not copy_row["checks"]["surface_changed"], copy_row

reversed_story = copy.deepcopy(GOOD)
reversed_story["STORY_B"] = (
    "ORION-7 gave SILVER-RING to MIRA-1. "
    "ORION-7 crossed TUNNEL-4 with the ring. "
    "ORION-7 found SILVER-RING at GATE-2."
)
story_result = gate.evaluate_suite(reversed_story)
story_row = next(x for x in story_result["results"] if x["probe_id"] == "STORY_B")
assert not story_row["pass"], story_row
assert not story_row["checks"]["semantic_event_order"], story_row

nonsense = {p.probe_id: "alpha beta gamma." for p in gate.frozen_probes()}
nonsense_result = gate.evaluate_suite(nonsense)
assert not nonsense_result["pass"], nonsense_result
assert nonsense_result["case_pass_count"] == 0, nonsense_result

missing = copy.deepcopy(GOOD)
missing.pop("SUM_A")
missing_result = gate.evaluate_suite(missing)
assert not missing_result["pass"], missing_result

receipt = {
    "schema": "PROJECT_BRAIN_ROOT1_CONTRASTIVE_SEMANTIC_GATE_INDEPENDENT_VERIFICATION_V1",
    "status": "PASS",
    "source_git_blob_sha": actual_blob,
    "positive_suite": "8_OF_8_PASS",
    "adversarial_checks": [
        "COUNTERFACTUAL_FACT_FLIP_REJECTED",
        "VERBATIM_PARAPHRASE_REJECTED",
        "REVERSED_EVENT_ORDER_REJECTED",
        "STRUCTURAL_NONSENSE_REJECTED",
        "MISSING_PROBE_FAILS_CLOSED"
    ],
    "terminal_case_exposure": 0,
    "incremental_spend_usd": 0,
    "acceptance_credit": 0,
    "hard_nonclaim": "THIS_VERIFIES_THE_GATE_IMPLEMENTATION_AND_ADVERSARIAL_BEHAVIOR_ONLY; IT DOES_NOT QUALIFY_ANY MODEL OR PROVE OPUS_5_5_PARITY."
}
print(json.dumps(receipt, indent=2, sort_keys=True))
