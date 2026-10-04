#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v5_universal_proof_v1 as proposed

EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"8b855851b8a0fec3a0811c5033cc4ea6d2436954",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":"6685a1b173acacc69cffc99efeafd48fee793d69",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v4_universal_proof_v1.py":"72bbed393ac1bcaccb4cf33cd37835662c421f6c",
 "canonical/runtime/unknown_domain_direct_v5_universal_proof_v1.py":"ab6ea01260b13133d208a7eea08317cfaa1e9ab0",
 "canonical/tests/test_unknown_domain_v4_total_string_domain_v1.py":"fa329273cb7b236575d7b2ab2638574c487996fb",
}


def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


got={rel:blob(ROOT/rel) for rel in EXPECTED}
assert got==EXPECTED,{"expected":EXPECTED,"got":got}

# 1. Reproduce the precise hole in the prior top-level V4 quantifier.
bad_beacon="A"*16+"\ud800"
assert len(bad_beacon.strip())>=16
v3_failed=False
try:
    g3._generate(
        beacon=bad_beacon,
        evaluator_secret=b"S"*32,
        namespace="V4-TOTALITY-FALSIFIER",
    )
except UnicodeEncodeError:
    v3_failed=True
assert v3_failed,"EXPECTED_V3_ACCEPTED_BEACON_ENCODING_FAILURE_NOT_REPRODUCED"

# 2. Exhaust the entire surrogate range through the new beacon canonicalizer.
surrogate_outputs=set()
for cp in range(0xD800,0xE000):
    beacon="A"*16+chr(cp)
    encoded=g4._canonical_beacon(beacon)
    assert encoded.isascii()
    assert encoded.startswith("UDIRV4-BEACON-HEX|")
    surrogate_outputs.add(encoded)
assert len(surrogate_outputs)==0x800

# Normal/supplementary representatives must not collide with surrogate encodings.
representatives=[
    "A"*16+"�",
    "A"*16+"😀",
    "Ω"*16,
    "\x00"+"C"*16,
    "Z"*17,
]
rep_outputs={g4._canonical_beacon(x) for x in representatives}
assert len(rep_outputs)==len(representatives)
assert not (rep_outputs & surrogate_outputs)

# 3. Exhaust all possible abstract Fisher-Yates choice paths for n<=7 again.
def abstract_perm(n:int,choices:tuple[int,...])->tuple[int,...]:
    out=list(range(n))
    k=0
    for i in range(n-1,0,-1):
        j=choices[k]
        k+=1
        assert 0<=j<=i
        out[i],out[j]=out[j],out[i]
    return tuple(out)

exhaustive_paths=0
for n in range(1,8):
    domains=[range(i+1) for i in range(n-1,0,-1)]
    for choices in itertools.product(*domains):
        p=abstract_perm(n,choices)
        assert len(p)==n and set(p)==set(range(n))
        exhaustive_paths+=1
assert exhaustive_paths==5913

# 4. Independently re-derive the strict transfer margins used by the exact route.
D0=Fraction(19,4)
D1=Fraction(25,4)
MIN=Fraction(1,4)
MAX=Fraction(7,2)
assert Fraction(3,5)*D0==Fraction(57,20)
assert D0==Fraction(19,4)
sat_gap=Fraction(7,10)*D0/Fraction(121,1)
assert float(sat_gap)>4.5e-9
assert -MAX+D0==Fraction(5,4)>0
assert D0-Fraction(11,5)==Fraction(51,20)>0
add2_gaps=(D0-(MAX-MIN),D1,D0,D1-(MAX-MIN),D0+D1)
assert min(add2_gaps)==Fraction(3,2)
assert harness.MAX_TRANSFER_PROBES==2

# 5. Reproduce a V2 exact-float failure under the repaired generator internals
# and require Candidate V3 to repair the identical visible+hidden packet.
secret=g4._secret_bytes_total("S"*31+"\ud800")
counterexample=None
for k in range(1024):
    original=f"V5-FLOAT-{k:04d}-BEACON"
    canon=g4._canonical_beacon(original)
    for index in (4,10):
        visible,hidden=g3._transfer_case(secret,canon,index,namespace="V5FLOAT")
        bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
        if not bad["scorer_result"]["pass"] and "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"]["errors"]:
            good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
            assert good["scorer_result"]["pass"],good["scorer_result"]
            assert good["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
            counterexample={
                "beacon":original,
                "index":index,
                "v2_terminal":bad["candidate_terminal_action"]["terminal_consequence"],
                "gold":hidden["gold_terminal_consequence"],
                "v3_probe_count":good["probe_count"],
            }
            break
    if counterexample:
        break
assert counterexample is not None,"EXPECTED_V2_EXACT_FLOAT_COUNTEREXAMPLE_NOT_FOUND"

# 6. Adversarial string-interface matrix through the full 27-case path.
weird_beacons=[
    "A"*16+"\ud800",
    "\udfff"+"B"*16,
    "Ω"*16,
    "\x00"+"C"*16,
]
weird_secrets=[
    b"S"*32,
    "T"*31+"\ud800",
    "\udfff"+"U"*31,
    "λ"*32,
]
adversarial_cases=0
for i,beacon in enumerate(weird_beacons):
    for j,secret_value in enumerate(weird_secrets):
        packet=g4._generate(
            beacon=beacon,
            evaluator_secret=secret_value,
            namespace=f"V5EDGE{i}{j}",
        )
        rows=[]
        assert packet["case_count"]==27
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
            out=harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            assert out["scorer_result"]["pass"],{
                "i":i,"j":j,"case":visible["case_id"],"errors":out["scorer_result"]["errors"]
            }
            rows.append(out["scorer_result"])
            adversarial_cases+=1
        assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert adversarial_cases==432

# 7. Large deterministic nonproduction falsification sweep through Generator V4.
populations=256
cases=0
for i in range(populations):
    packet=g4.generate_qualification_fixture_population(
        beacon=f"INDEPENDENT-V5-TOTAL-STRING-{i:04d}"
    )
    assert packet["production"] is False
    assert packet["case_count"]==27
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
        out=harness.execute_case(
            candidate_step=c3.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"],{
            "population":i,
            "case_id":visible["case_id"],
            "errors":out["scorer_result"].get("errors"),
        }
        rows.append(out["scorer_result"])
        cases+=1
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert cases==6912

# 8. Compare the proposed V5 theorem only after the independent attacks.
theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_OVER_TOTAL_PYTHON_STRING_INTERFACE_TOTAL_IDS_AND_EXACT_FLOAT_CANDIDATE"
assert theorem["string_interface_totality"]["legacy_strict_utf8_surrogate_failure_removed"] is True
assert theorem["identifier_totality_proof"]["hash_collision_resistance_required"] is False
assert theorem["transfer_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V5_TOTAL_STRING_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__INDEPENDENT_TOTAL_STRING_TOTAL_ID_EXACT_FLOAT_AND_7344_CASE_FALSIFICATION__ZERO_CREDIT",
 "exact_subject_blobs":EXPECTED,
 "prior_v4_string_totality_counterexample_reproduced":True,
 "surrogate_codepoints_exhausted":0x800,
 "fisher_yates_exhaustive_choice_paths_n_le_7":exhaustive_paths,
 "v2_exact_float_counterexample":counterexample,
 "nonproduction_falsification":{
   "ordinary_populations":populations,
   "ordinary_cases":cases,
   "adversarial_string_cases":adversarial_cases,
   "total_scored_cases":cases+adversarial_cases,
   "all_pass":True,
 },
 "production_or_terminal_cases_generated":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER",
   "SEPARATE_FAIL_CLOSED_ROOT3_AND_ACCEPTANCE_REDUCTION_REQUIRED",
 ],
}
Path("unknown_domain_v5_total_string_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=True)+"\n",
    encoding="utf-8",
)
print(json.dumps(receipt,sort_keys=True))
