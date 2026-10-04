#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":"e52858b9fef2d795f72b45cd3ae82ad04344aa91",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"a97459fe407ea4852f57f12f504fbc0121db9824",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/tests/test_unknown_domain_direct_v5.py":"81cd6ecabec51029175f6036a13eac7667fccd03",
 "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py":"58410966e17c1bc546db8cab039891f3ab2bf8a8",
}
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,want in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==want,(rel,got,want)

seen=set()
for cp in range(0xD800,0xE000):
    x=g5._canonical_beacon("A"*16+chr(cp))
    assert x.isascii()
    seen.add(x)
assert len(seen)==0x800
assert g5._secret_bytes_total("S"*31+"\ud800")
assert g5._secret_bytes_total("\udfff"+"T"*31)
assert g5._secret_bytes_total(b"U"*32)==b"U"*32

orig=g1._token
try:
    g1._token=lambda *a,**k:"COLLISION"
    labels=g4._ranked_labels(b"x"*32,"V5:4141",scope="V6VERIFY",keys=[f"k{i}" for i in range(27)],prefix="Q-")
    assert len(labels)==27 and len(set(labels.values()))==27
    packet=g5._generate(
        beacon="A"*16+"\ud800",
        evaluator_secret="S"*31+"\udfff",
        namespace="V6VERIFY",
    )
finally:
    g1._token=orig
assert packet["case_count"]==27
assert len({x["case_id"] for x in packet["visible_cases"]})==27

results=[]
for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
    out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
    assert out["scorer_result"]["pass"] is True,(visible["case_id"],out)
    results.append(out["scorer_result"])
assert scorer.aggregate(results)["all_27_cases_pass"] is True

d0=Fraction(19,4); d1=Fraction(25,4)
mn=Fraction(1,4); mx=Fraction(7,2)
assert Fraction(3,5)*d0==Fraction(57,20)
assert d0==Fraction(19,4)
assert float(Fraction(7,10)*d0/Fraction(121,1))>4.5e-9
assert -mx+d0==Fraction(5,4)>0
assert d0-Fraction(11,5)==Fraction(51,20)>0
assert min((d0-(mx-mn),d1,d0,d1-(mx-mn),d0+d1))==Fraction(3,2)
for index in (4,10):
    r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
    r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
    assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
    assert r1==c3.ADD2_R1_SIG==(1,-1,1)

proof=proposed.prove(ROOT)
assert proof["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert proof["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert proof["scope"]["population_cases"]==27
assert proof["scope"]["terminal_or_production_cases_generated"]==0
assert proof["fresh_reality_required_for_this_exact_bound_evaluator_claim"] is False
assert proof["production_execution_information_gain_for_this_exact_bound_evaluator_claim"]==0
assert proof["accounting"]["acceptance_credit_delta"]==0

print(json.dumps({
 "status":"INDEPENDENT_UNKNOWN_DOMAIN_V6_UNIVERSAL_TOTALITY_PASS",
 "exact_subject_blob_count":len(EXPECTED),
 "surrogate_codepoints_exhausted":0x800,
 "forced_total_token_collision_survives":True,
 "nonproduction_cases_exact_scorer_pass":27,
 "fresh_reality_required_for_bound_claim":False,
 "production_execution_information_gain":0,
 "open_world_claim":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
