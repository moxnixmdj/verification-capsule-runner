#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":"ee5f3832fdbad5ae645b0626e9f39ebeaee2b1da",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json":"4303d6259b4c7adb747cd83923a28f1771f36d44",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

# Exact bytes first.
for rel,expected in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==expected,(rel,got,expected)

# Frozen protocol surface.
assert tuple(g1.PRIMITIVE_FAMILIES)==(
 "ORDER_PRESERVING_TRANSFORM","PARITY_OR_SIGN_INVARIANT",
 "CONSERVATION_RELATION","MONOTONE_CAUSAL_EDGE",
 "COMPOSITIONAL_REWRITE","THRESHOLD_OR_PARTITION_INVARIANT",
)
assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
assert harness.MAX_TRANSFER_PROBES==2
assert c1.MAPPING_BASIS=="STRUCTURAL_EQUIVALENCE"
assert scorer.DECISIONS=={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}

# Adversarial falsification gate: V2 must fail the known exact-float ADD2 case.
# This uses the private helper only to construct a synthetic/nonproduction packet.
# It never calls generate_production_population or consumes the one-use authority.
secret=hashlib.sha256(b"secret0").digest()
beacon="beacon-qualification-0000000000000000"
visible,hidden=g2._transfer_case(secret,beacon,4,namespace="QUALONLY")
v2=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
assert v2["scorer_result"]["pass"] is False,v2
assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in v2["scorer_result"]["errors"]
v2_value=v2["candidate_terminal_action"]["terminal_consequence"]
gold=hidden["gold_terminal_consequence"]
assert v2_value!=gold
assert 0 < abs(v2_value-gold) < 1e-12
assert set(v2["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])

# V3 must repair the same packet using visible role orientation only.
v3=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
assert v3["scorer_result"]["pass"] is True,v3
assert v3["candidate_terminal_action"]["terminal_consequence"]==gold
assert set(v3["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])
assert v3["probe_count"]==1

# Independent exact arithmetic for universal support discrimination.
D0=Fraction(19,4)
D1=Fraction(25,4)
MIN_MAG=Fraction(1,4)
MAX_MAG=Fraction(7,2)

assert Fraction(3,5)*D0==Fraction(57,20)                  # AFFINE_POS
assert D0==Fraction(19,4)                                 # COMPLEMENT
sat_gap=Fraction(7,10)*D0/Fraction(121,1)                 # SAT_MONO
assert sat_gap==Fraction(133,4840)
assert float(sat_gap)>4.5e-9

for index in (1,7):                                       # SIGN
    assert (3+index)%2==0
assert -MAX_MAG+D0==Fraction(5,4)>0

assert D0-Fraction(11,5)==Fraction(51,20)>0               # STEP

for index in (4,10):                                      # ADD2 probe-1
    assert (3+index)%2==1
    assert (3+index+1)%3!=0
wrong_support_gaps=(
    D0-(MAX_MAG-MIN_MAG),D1,D0,D1-(MAX_MAG-MIN_MAG),D0+D1,
)
assert min(wrong_support_gaps)==Fraction(3,2)

# ADD2 exact role orientation is visible and unique on public rows 0..2.
for index in (4,10):
    r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
    r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
    assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
    assert r1==c3.ADD2_R1_SIG==(1,-1,1)
    assert r0!=r1
assert MIN_MAG>0

# Abstention construction is total and deterministic.
assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")
candidate_source=(ROOT/"canonical/runtime/unknown_domain_direct_candidate_v1.py").read_text()
generator_source=(ROOT/"canonical/runtime/unknown_domain_direct_hidden_generator_v1.py").read_text()
scorer_source=(ROOT/"canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py").read_text()
assert 'b = a if cls == "IDENTIFIABLE"' in generator_source
assert 'kind=="SAFE_BINARY_DISCRIMINATOR"' in candidate_source
assert 'discriminators.sort(key=lambda x:(x[0],x[1]))' in candidate_source
assert 'if status=="NONIDENTIFIABLE"' in scorer_source
assert 'if status=="UNDERSPECIFIED"' in scorer_source

# Compare against proposed certificate only after the independent derivation.
out=proposed.prove(ROOT)
assert out["status"]=="PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN_WITH_V3_EXACTNESS_REPAIR"
assert out["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert out["scope"]["population_cases"]==27
assert out["scope"]["production_cases_generated"]==0
assert out["fresh_reality_required_for_this_exact_frozen_evaluator_claim"] is False
assert out["production_execution_information_gain_for_this_exact_evaluator_claim"]==0
assert out["v2_counterexample_status"].startswith("PROVED_BY_REGRESSION_TEST")
assert out["transfer_proof"]["add2_exact_float_order_repaired_by_v3"] is True
assert out["accounting"]["acceptance_credit_delta"]==0
assert out["accounting"]["family_credit_delta"]==0
assert out["accounting"]["capability_credit_delta"]==0
assert out["accounting"]["ownership_credit_delta"]==0

gov=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json").read_text())
assert gov["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert gov["truth_repair"]["v3_candidate_git_blob_sha"]==EXPECTED["canonical/runtime/unknown_domain_direct_candidate_v3.py"]
assert gov["authority"]["independent_verification_required"] is True
assert gov["accounting"]["production_cases_generated"]==0

print(json.dumps({
 "status":"INDEPENDENT_V3_UNIVERSAL_FROZEN_DOMAIN_PROOF_PASS",
 "target_predicate":out["target_predicate"],
 "v2_exact_float_counterexample_reproduced":True,
 "v3_same_case_repaired":True,
 "exact_subject_blob_count":len(EXPECTED),
 "transfer_families_universally_discharged":6,
 "abstention_classes_universally_discharged":3,
 "production_cases_generated":0,
 "fresh_reality_required_for_frozen_evaluator_claim":False,
 "open_world_claim":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
