#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proposed

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
 "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py":"58410966e17c1bc546db8cab039891f3ab2bf8a8",
 "canonical/tests/test_unknown_domain_direct_v5.py":"81cd6ecabec51029175f6036a13eac7667fccd03",
}

def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

got={rel:blob(ROOT/rel) for rel in EXPECTED}
assert got==EXPECTED, {"expected":EXPECTED,"got":got}

# Independent string-interface falsification/proof checks.
# Exhaust every single Python code point in a valid beacon context, including
# all surrogates, whitespace, noncharacters, and astral values. Round-trip the
# exact surrogatepass bytes carried by the V5 ASCII hex representation.
prefix="UDIRV5-BEACON-HEX|"
codepoints=0
for cp in range(0x110000):
    original="A"*16+chr(cp)
    canonical=g5._canonical_beacon(original)
    assert canonical.startswith(prefix)
    assert canonical.isascii()
    payload=bytes.fromhex(canonical[len(prefix):])
    assert payload.decode("utf-8","surrogatepass")==original
    codepoints+=1
assert codepoints==0x110000

# The concrete V4 counterexample remains reachable and V5 removes it.
surrogate_beacon="A"*16+"\ud800"
try:
    g4._generate(beacon=surrogate_beacon,evaluator_secret=b"X"*32,namespace="V4FAIL")
except UnicodeEncodeError:
    v4_counterexample=True
else:
    raise AssertionError("EXPECTED_V4_UNPAIRED_SURROGATE_FAILURE")

edge_secrets=[
    b"S"*32,
    "T"*31+"\ud800",
    "\udfff"+"U"*31,
    "λ"*32,
]
edge_beacons=[
    "A"*16+"\ud800",
    "\udfff"+"B"*16,
    "Ω"*16,
    "\x00"+"C"*16,
    "Z"*16+"😀",
]
for i,b in enumerate(edge_beacons):
    for j,s in enumerate(edge_secrets):
        packet=g5._generate(beacon=b,evaluator_secret=s,namespace=f"V6EDGE{i}{j}")
        assert packet["case_count"]==27

# Structural ID totality must not depend on token collision resistance.
# Force every rank/suffix token to the exact same string and score the complete
# population, not merely identifier cardinalities.
original_token=g1._token
try:
    g1._token=lambda *args,**kwargs:"COLLISION"
    collision_packet=g5._generate(
        beacon="A"*16+"\ud800",
        evaluator_secret="S"*31+"\udfff",
        namespace="V6COLLIDE",
    )
    assert len({x["case_id"] for x in collision_packet["visible_cases"]})==27
    collision_rows=[]
    for visible,hidden in zip(collision_packet["visible_cases"],collision_packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out)
        collision_rows.append(out["scorer_result"])
    assert scorer.aggregate(collision_rows)["all_27_cases_pass"] is True
finally:
    g1._token=original_token

# Independently bind exact ADD2 operation order in both gold and candidate.
gen_src="".join(inspect.getsource(g1._eval).split())
cand_src="".join(inspect.getsource(c1._program_eval).split())
assert 'returnfloat(p["bias"])+float(role_values["r0"])+float(role_values["r1"])' in gen_src
assert 'return_finite(params["bias"],"bias")+_finite(role_values["r0"],"r0")+_finite(role_values["r1"],"r1")' in cand_src
assert c3.ADD2_R0_SIG==(-1,1,-1)
assert c3.ADD2_R1_SIG==(1,-1,1)
assert g4.v2 is g2
assert g5.v4 is g4

# Find a live exact-float V2 failure after V5 canonicalization, then require V3
# to repair the exact same visible/hidden packet. This guards against a proof
# that accidentally repairs only an obsolete generator.
float_counterexample=None
secret=hashlib.sha256(b"INDEPENDENT-V6-FLOAT-SEARCH").digest()
for k in range(2048):
    packet=g5._generate(
        beacon=f"INDEPENDENT-V6-FLOAT-{k:04d}-BEACON",
        evaluator_secret=secret,
        namespace="V6FLOAT",
    )
    for index in (4,10):
        visible=packet["visible_cases"][index]
        hidden=packet["hidden_records"][index]
        bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
        if (bad["scorer_result"]["pass"] is False
            and "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"]["errors"]):
            good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
            assert good["scorer_result"]["pass"] is True,good
            assert good["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
            float_counterexample={
                "beacon_index":k,
                "transfer_index":index,
                "v2":bad["candidate_terminal_action"]["terminal_consequence"],
                "gold":hidden["gold_terminal_consequence"],
                "v3_probe_count":good["probe_count"],
            }
            break
    if float_counterexample is not None:
        break
assert float_counterexample is not None,"EXPECTED_POST_V5_V2_EXACT_FLOAT_COUNTEREXAMPLE"

# Large deterministic nonproduction falsification sweep over the exact V5 route.
populations=256
cases=0
for i in range(populations):
    beacon="V6-INDEPENDENT-"+hashlib.sha256(f"beacon-{i}".encode()).hexdigest()
    packet=g5.generate_qualification_fixture_population(beacon=beacon)
    assert packet["production"] is False
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,{
            "population":i,
            "case_id":visible["case_id"],
            "errors":out["scorer_result"].get("errors"),
        }
        rows.append(out["scorer_result"])
        cases+=1
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert cases==6912

# Only after independent derivation and falsification do we evaluate Brain's proof.
theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["string_interface_totality"]["legacy_strict_utf8_partiality_removed"] is True
assert theorem["identifier_totality_proof"]["token_collision_resistance_required_for_semantic_distinctness"] is False
assert theorem["transfer_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_TOTAL_STRING_EXACT_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__INDEPENDENT_CONTENT_BOUND_TOTAL_STRING_STRUCTURAL_ID_EXACT_FLOAT_AND_6912_CASE_FALSIFICATION__ZERO_CREDIT",
 "exact_subject_blobs":EXPECTED,
 "python_codepoints_roundtripped":codepoints,
 "v4_unpaired_surrogate_counterexample_preserved":v4_counterexample,
 "forced_total_token_collision_full_population_pass":True,
 "post_v5_v2_exact_float_counterexample":float_counterexample,
 "nonproduction_falsification":{"populations":populations,"cases":cases,"all_pass":True},
 "production_or_terminal_cases_generated":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER",
   "SEPARATE_FAIL_CLOSED_ROOT3_AND_ACCEPTANCE_REDUCTION_REQUIRED",
 ],
}
Path("unknown_domain_v6_total_string_exact_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=True)+"\n",
    encoding="utf-8",
)
print(json.dumps(receipt,sort_keys=True,ensure_ascii=True))
