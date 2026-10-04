#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/unknown_domain_v6_20261005"
sys.path.insert(0,str(SUBJECT))

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
def blob(path):
    return subprocess.run(["git","hash-object",str(path)],check=True,text=True,capture_output=True).stdout.strip()
for rel,sha in EXPECTED.items():
    got=blob(SUBJECT/rel)
    assert got==sha,(rel,sha,got)

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof

p=proof.prove(SUBJECT)
assert p["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert p["fresh_reality_required_for_this_exact_bound_evaluator_claim"] is False
assert p["production_execution_information_gain_for_this_exact_bound_evaluator_claim"]==0

# Independent implementation check of the total string seam.
seen=set()
for cp in range(0xD800,0xE000):
    s="A"*16+chr(cp)
    out=g5._canonical_beacon(s)
    assert out.startswith("UDIRV5-BEACON-HEX|")
    assert out.isascii()
    expected="UDIRV5-BEACON-HEX|"+s.encode("utf-8","surrogatepass").hex()
    assert out==expected
    seen.add(out)
assert len(seen)==2048
for s in ["Ω"*16,"😀"*16,"\x00"+"C"*16,"A"*16+"�"]:
    out=g5._canonical_beacon(s)
    assert out=="UDIRV5-BEACON-HEX|"+s.encode("utf-8","surrogatepass").hex()
    assert out not in seen

def execute_packet(packet):
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out["scorer_result"])
        rows.append(out["scorer_result"])
    agg=scorer.aggregate(rows)
    assert agg["all_27_cases_pass"] is True
    return len(rows)

# Strong collision adversary: all legacy token calls collapse to one literal.
orig=g1._token
try:
    g1._token=lambda *args,**kwargs:"COLLISION"
    collision_packet=g5._generate(
        beacon="A"*16+"\ud800",
        evaluator_secret="S"*31+"\udfff",
        namespace="V6-INDEPENDENT-COLLISION",
    )
    assert len({x["case_id"] for x in collision_packet["visible_cases"]})==27
    collision_cases=execute_packet(collision_packet)
finally:
    g1._token=orig

# Independent broad deterministic sweep over the full exact 27-case evaluator.
scored=0
for k in range(256):
    h=hashlib.sha256(f"independent-v6-{k}".encode()).hexdigest()
    beacon=("V6-"+h[:24]) if k%4 else ("B"*16+chr(0xD800+(k%0x800)))
    if k%5==0:
        secret="Q"*31+chr(0xD800+((k*17)%0x800))
    else:
        secret=hashlib.sha256(f"secret-{k}".encode()).digest()
    packet=g5._generate(beacon=beacon,evaluator_secret=secret,namespace=f"INDV6-{k}")
    assert packet["case_count"]==27
    assert len({x["case_id"] for x in packet["visible_cases"]})==27
    scored+=execute_packet(packet)
assert scored==6912
assert tuple(c3.ADD2_R0_SIG)==(-1,1,-1)
assert tuple(c3.ADD2_R1_SIG)==(1,-1,1)

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_INDEPENDENT_UNIVERSAL_VERIFICATION_20261005_V1",
 "status":"PASS__EXACT_BOUND_V6_TOTAL_STRING_STRUCTURAL_IDS_EXACT_FLOAT__ZERO_PRODUCTION_CASES",
 "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
 "brain_source_commit":"75a087e8ce2892f74ac4120285d0b9157decfbee",
 "subject_blobs":EXPECTED,
 "verified":{
   "brain_content_bound_proof_pass":True,
   "surrogate_codepoints_exhausted":2048,
   "canonicalization_matches_surrogatepass_hex":True,
   "forced_total_token_collision_full_population_cases":collision_cases,
   "independent_populations":256,
   "independent_exact_scorer_cases":scored,
   "all_exact_scorer_cases_pass":True,
   "add2_role_signatures_exact":True
 },
 "scope":{
   "bound_evaluator_cases":27,
   "transfer_cases":12,
   "abstention_cases":15,
   "production_cases_generated":0,
   "terminal_cases_read":0
 },
 "hard_nonclaims":[
   "NO_OPEN_WORLD_GENERALIZATION_BEYOND_THE_EXACT_BOUND_EVALUATOR_CONTRACT",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_RECEIPT_ALONE",
   "SEPARATE_ROOT3_AND_ACCEPTANCE_REDUCTION_REMAINS_REQUIRED"
 ],
 "accounting":{"incremental_spend_usd":0,"acceptance_credit_delta":0}
}
path=ROOT/"unknown_domain_v6_independent_receipt.json"
path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
