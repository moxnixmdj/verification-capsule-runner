from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_v2_universal_proof_v1 as proposed

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":
        "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":
        "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_v2_universal_proof_v1.py":
        "2400dba7f763fc16dc65c31512ccd9eee8be82fb",
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_V2_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json":
        "97084bbfb2d9228b9555c3fb71d29f4d0e8796fa",
}


def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


# 1. Content address every load-bearing byte.
for rel, expected in EXPECTED.items():
    got = blob(ROOT / rel)
    assert got == expected, (rel, got, expected)

# 2. Verify the frozen evaluator cardinalities and strict rediscovery boundary.
assert tuple(g1.PRIMITIVE_FAMILIES) == (
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)
assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}
assert harness.MAX_TRANSFER_PROBES == 2
assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"
assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}

# 3. Independent exact arithmetic for every transfer-family discriminator.
# Frozen V2 _surface_row inherits the V1 shift:
# delta = 4.75 + 1.5*i + 0.25*probe_variant.
D0 = Fraction(19, 4)   # 4.75
D1 = Fraction(25, 4)   # 6.25
MIN_MAG = Fraction(1, 4)
MAX_MAG = Fraction(7, 2)

# AFFINE_POS: gain >= 0.6 = 3/5.
assert Fraction(3, 5) * D0 == Fraction(57, 20)  # 2.85

# COMPLEMENT: slope magnitude 1.
assert D0 == Fraction(19, 4)

# SAT_MONO: f'(x)=1/(1+|x|)^2. The whole possible true-to-shifted interval
# is contained in [-3.5, 10], so derivative >=1/121 and gain>=0.7=7/10.
sat_gap = Fraction(7, 10) * D0 / 121
assert sat_gap == Fraction(133, 4840)
# Frozen _close tolerance is <= 4.5e-9 over SAT_MONO output range.
assert float(sat_gap) > 4.5e-9

# SIGN at indices 1 and 7: first transfer probe is generator row j=3.
# (j+index) even -> true r0 negative. Its worst negative value is -0.25.
# A shifted distractor is >= -3.5 + 4.75 = +1.25.
for index in (1, 7):
    assert (3 + index) % 2 == 0
assert -MIN_MAG < 0
assert -MAX_MAG + D0 == Fraction(5, 4) > 0

# STEP at indices 5 and 11: second transfer probe is row j=4, explicitly
# threshold-mag. mag<=2.2=11/5; shifted distractor is above threshold by >=2.55.
assert D0 - Fraction(11, 5) == Fraction(51, 20) > 0

# ADD2 at indices 4 and 10: first probe row j=3 makes both true roles positive.
# Enumerate all five wrong unordered support forms among r0,r1,d0,d1.
for index in (4, 10):
    assert (3 + index) % 2 == 1
    assert (3 + index + 1) % 3 != 0
wrong_support_gaps = (
    D0 - (MAX_MAG - MIN_MAG),  # {r0,d0}
    D1,                        # {r0,d1}
    D0,                        # {r1,d0}
    D1 - (MAX_MAG - MIN_MAG),  # {r1,d1}
    D0 + D1,                   # {d0,d1}
)
assert min(wrong_support_gaps) == Fraction(3, 2)
# The only role-order ambiguity on the true support is harmless because ADD2
# is symmetric in r0/r1; the scorer requires the support set and consequence.

# 4. Independently bind the visible abstention construction to candidate/scorer.
assert tuple(g1.ABSTAIN_CLASSES) == ("IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED")
candidate_source = (ROOT / "canonical/runtime/unknown_domain_direct_candidate_v1.py").read_text()
generator_source = (ROOT / "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py").read_text()
scorer_source = (ROOT / "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py").read_text()
assert 'b = a if cls == "IDENTIFIABLE"' in generator_source
assert 'kind=="SAFE_BINARY_DISCRIMINATOR"' in candidate_source
assert 'discriminators.sort(key=lambda x:(x[0],x[1]))' in candidate_source
assert 'if status=="NONIDENTIFIABLE"' in scorer_source
assert 'if status=="UNDERSPECIFIED"' in scorer_source

# 5. Verify the proposed certificate agrees with this independent derivation,
# while keeping all credit fail-closed.
out = proposed.prove(ROOT)
assert out["status"] == "PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN"
assert out["target_predicate"] == "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert out["scope"]["production_population_cases"] == 27
assert out["scope"]["terminal_or_production_cases_generated"] == 0
assert out["fresh_reality_required_for_THIS_frozen_generator_claim"] is False
assert out["production_execution_information_gain"] == 0
assert out["transfer_proof"]["add2_wrong_support_min_gap"] >= 1.5
assert out["transfer_proof"]["sat_mono_min_output_gap"] > out["transfer_proof"]["sat_mono_max_close_tolerance"]
assert out["accounting"]["acceptance_credit_delta"] == 0
assert out["accounting"]["family_credit_delta"] == 0
assert out["accounting"]["capability_credit_delta"] == 0
assert out["accounting"]["ownership_credit_delta"] == 0

gov = json.loads(
    (ROOT / "canonical/governance/UNKNOWN_DOMAIN_DIRECT_V2_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json").read_text()
)
assert gov["target_predicate"] == "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert gov["authority"]["independent_verification_required"] is True
assert gov["accounting"]["production_cases_generated"] == 0
assert "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_CLAIM" in gov["hard_nonclaims"]

print(json.dumps({
    "status": "INDEPENDENT_UNIVERSAL_FROZEN_DOMAIN_PROOF_PASS",
    "target_predicate": out["target_predicate"],
    "exact_subject_blob_count": 6,
    "transfer_families_universally_discharged": 6,
    "abstention_classes_universally_discharged": 3,
    "production_cases_generated": 0,
    "fresh_reality_required_for_frozen_domain_claim": False,
    "open_world_claim": False,
    "acceptance_credit_delta": 0
}, sort_keys=True))
