#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parents[1]
EXPECTED=dict(proposed.EXPECTED_BLOBS)

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

got={rel:blob(ROOT/rel) for rel in EXPECTED}
assert got==EXPECTED,{"expected":EXPECTED,"got":got}

# Independently split the Python str domain: non-surrogate code points are
# ordinary UTF-8; all 2048 surrogate code points are explicitly exhausted under
# surrogatepass. The byte stream is then hex encoded, which is injective.
surrogate_outputs=set()
for cp in range(0xD800,0xE000):
    s="A"*16+chr(cp)
    raw=s.encode("utf-8","surrogatepass")
    out=g5._canonical_beacon(s)
    assert out=="UDIRV5-BEACON-HEX|"+raw.hex()
    assert out.isascii()
    surrogate_outputs.add(out)
assert len(surrogate_outputs)==0x800

non_surrogate_samples=[
    "A"*16+"\x00","A"*16+"Ω","A"*16+"😀","A"*16+"\U0010ffff",
]
ordinary={g5._canonical_beacon(x) for x in non_surrogate_samples}
assert not (ordinary & surrogate_outputs)

# Structural identifiers must remain unique even if every legacy token collides.
orig=g1._token
try:
    g1._token=lambda *a,**k:"COLLISION"
    for n in (1,2,3,4,12,15,27):
        keys=[f"k{i}" for i in range(n)]
        labels=g4._ranked_labels(
            b"x"*32,"ASCII-CANONICAL-BEACON-0000",
            scope=f"INDEPENDENT-{n}",keys=keys,prefix="Q-")
        assert len(labels)==n==len(set(labels.values()))
    packet=g5._generate(
        beacon="A"*16+"\ud800",
        evaluator_secret="S"*31+"\udfff",
        namespace="V6INDEPENDENTCOLLISION")
    assert len({r["case_id"] for r in packet["visible_cases"]})==27
finally:
    g1._token=orig

# Independent end-to-end nonproduction falsification over ordinary and
# surrogate-bearing inputs, using the exact scorer/harness.
beacons=[
    "A"*16+"\ud800","\udfff"+"B"*16,"Ω"*16,"\x00"+"C"*16,
]
secrets=[
    b"S"*32,"T"*31+"\ud800","\udfff"+"U"*31,"λ"*32,
]
cases=0
for i,b in enumerate(beacons):
    for j,s in enumerate(secrets):
        packet=g5._generate(beacon=b,evaluator_secret=s,namespace=f"V6EDGE{i}{j}")
        rows=[]
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
            out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
            assert out["scorer_result"]["pass"],(visible["case_id"],out["scorer_result"])
            rows.append(out["scorer_result"]); cases+=1
        assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert cases==432

# Larger deterministic ordinary-string sweep.
for k in range(128):
    secret=hashlib.sha256(f"v6-independent-{k}".encode()).digest()
    beacon="V6-INDEPENDENT-"+hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
    packet=g5._generate(beacon=beacon,evaluator_secret=secret,namespace=f"V6S{k}")
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"],(k,visible["case_id"],out["scorer_result"])
        rows.append(out["scorer_result"]); cases+=1
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert cases==3888

theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert theorem["string_interface_totality"]["surrogate_codepoints_exhausted"]==2048
assert theorem["identifier_totality_proof"]["forced_total_token_collision_survives_construction"] is True
assert theorem["transfer_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
  "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_INDEPENDENT_VERIFICATION_V1",
  "status":"PASS__CONTENT_BOUND_TOTAL_STRING_STRUCTURAL_ID_EXACT_FLOAT_AND_3888_CASE_FALSIFICATION__ZERO_REALITY",
  "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
  "exact_subject_blobs":EXPECTED,
  "surrogate_codepoints_exhausted":2048,
  "forced_total_token_collision_survives":True,
  "nonproduction_falsification_cases":cases,
  "production_or_terminal_cases_generated":0,
  "acceptance_credit_delta":0,
  "hard_nonclaims":[
    "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_BOUND_EVALUATOR_CONTRACT",
    "SEPARATE_ROOT3_ACCEPTANCE_REDUCTION_REQUIRED"
  ]
}
Path("unknown_domain_v6_independent_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
