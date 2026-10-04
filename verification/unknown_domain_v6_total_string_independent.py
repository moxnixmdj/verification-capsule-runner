#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parents[1]

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
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

got={rel:blob(ROOT/rel) for rel in EXPECTED}
assert got==EXPECTED, {"expected":EXPECTED,"got":got}

# 1. Independently bind the actual implementation to total surrogatepass
# canonicalization before any legacy strict-UTF8 helper is reached.
beacon_src="".join(inspect.getsource(g5._canonical_beacon).split())
secret_src="".join(inspect.getsource(g5._secret_bytes_total).split())
assert '.encode("utf-8","surrogatepass")' in beacon_src
assert '.hex()' in beacon_src
assert 'return"UDIRV5-BEACON-HEX|"+raw.hex()' in beacon_src
assert '.encode("utf-8","surrogatepass")' in secret_src

# Exhaust every Python Unicode scalar/code-point slot including D800-DFFF
# through the exact V5 functions. Decode roundtrip establishes byte-level
# injectivity of the surrogatepass representation; hex is bijective on bytes.
unicode_codepoints=0
surrogate_codepoints=0
for cp in range(0x110000):
    ch=chr(cp)
    raw=ch.encode("utf-8","surrogatepass")
    assert raw.decode("utf-8","surrogatepass")==ch
    beacon="A"*16+ch
    canon=g5._canonical_beacon(beacon)
    assert canon=="UDIRV5-BEACON-HEX|"+beacon.encode("utf-8","surrogatepass").hex()
    assert canon.isascii()
    secret=g5._secret_bytes_total("S"*31+ch)
    assert secret==("S"*31+ch).encode("utf-8","surrogatepass")
    unicode_codepoints+=1
    if 0xD800<=cp<0xE000:
        surrogate_codepoints+=1
assert unicode_codepoints==0x110000
assert surrogate_codepoints==0x800

# 2. Preserve the concrete pre-repair failure: V4 accepts the string gate but
# legacy strict UTF-8 cannot encode a lone surrogate.
v4_surrogate_counterexample=False
try:
    g4._generate(beacon="A"*16+"\ud800",evaluator_secret=b"x"*32,namespace="V4FAIL")
except UnicodeEncodeError:
    v4_surrogate_counterexample=True
assert v4_surrogate_counterexample

# 3. Independently destroy every token-uniqueness assumption. V4/V5 must remain
# injective when every rank and suffix token is literally identical.
original_token=g1._token
try:
    g1._token=lambda *args,**kwargs:"COLLISION"
    for n in (1,2,3,4,12,15,27):
        labels=g4._ranked_labels(
            b"x"*32,
            "ASCII-CANONICAL-BEACON-0000",
            scope=f"VERIFY-TOTAL-{n}",
            keys=[f"k{i}" for i in range(n)],
            prefix="Q-",
        )
        assert len(labels)==n
        assert len(set(labels.values()))==n

    collision_packet=g5._generate(
        beacon="A"*16+"\ud800",
        evaluator_secret="S"*31+"\udfff",
        namespace="V6COLLIDE",
    )
    assert collision_packet["case_count"]==27
    assert len({x["case_id"] for x in collision_packet["visible_cases"]})==27
    collision_rows=[]
    for visible,hidden in zip(collision_packet["visible_cases"],collision_packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out["scorer_result"])
        collision_rows.append(out["scorer_result"])
    assert scorer.aggregate(collision_rows)["all_27_cases_pass"] is True
finally:
    g1._token=original_token

# 4. Re-derive the exact-float obligation and find a reachable V2 failure under
# the V5 canonicalized route. The same exact packet must pass Candidate V3.
gen_src="".join(inspect.getsource(g1._eval).split())
cand_src="".join(inspect.getsource(c1._program_eval).split())
assert 'returnfloat(p["bias"])+float(role_values["r0"])+float(role_values["r1"])' in gen_src
assert 'return_finite(params["bias"],"bias")+_finite(role_values["r0"],"r0")+_finite(role_values["r1"],"r1")' in cand_src
assert g4.v2 is g2

counterexample=None
search_secret=hashlib.sha256(b"INDEPENDENT-V6-FLOAT-SEARCH").digest()
for k in range(4096):
    raw_beacon=f"INDEPENDENT-V6-FLOAT-{k:04d}-BEACON"
    beacon=g5._canonical_beacon(raw_beacon)
    secret=g5._secret_bytes_total(search_secret)
    ids=g4._case_ids(secret,beacon,"V6VERIFY")
    for index in (4,10):
        visible,hidden=g4._transfer_case(
            secret,beacon,index,namespace="V6VERIFY",case_id=ids[f"T:{index}"]
        )
        bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
        if (not bad["scorer_result"]["pass"]
            and "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"].get("errors",[])):
            good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
            assert good["scorer_result"]["pass"],good["scorer_result"]
            assert good["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
            counterexample={
                "beacon":raw_beacon,
                "index":index,
                "v2":bad["candidate_terminal_action"]["terminal_consequence"],
                "gold":hidden["gold_terminal_consequence"],
                "v3_probe_count":good["probe_count"],
            }
            break
    if counterexample:
        break
assert counterexample is not None,"EXPECTED_V2_EXACT_FLOAT_COUNTEREXAMPLE_NOT_FOUND"

# 5. Deterministic nonproduction falsification across 256 independently varied
# V5 populations, including periodic surrogate-bearing beacons and secrets.
populations=256
cases=0
for i in range(populations):
    base="V6-VERIFY-"+hashlib.sha256(f"beacon-{i}".encode()).hexdigest()[:24]
    beacon=base+("\ud800" if i%17==0 else "")
    secret=("T"*31+"\udfff") if i%19==0 else hashlib.sha256(f"v6-secret-{i}".encode()).digest()
    packet=g5._generate(beacon=beacon,evaluator_secret=secret,namespace=f"V6T{i}")
    assert packet["case_count"]==27
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"],{
            "population":i,
            "case_id":visible["case_id"],
            "errors":out["scorer_result"].get("errors"),
        }
        rows.append(out["scorer_result"])
        cases+=1
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert cases==6912

# 6. Compare the independently established obligations against the proposed
# universal theorem only after falsification has passed.
theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert theorem["string_interface_totality"]["legacy_strict_utf8_partiality_removed"] is True
assert theorem["identifier_totality_proof"]["token_collision_resistance_required_for_semantic_distinctness"] is False
assert theorem["identifier_totality_proof"]["forced_total_token_collision_survives_construction"] is True
assert theorem["transfer_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_TOTAL_STRING_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__INDEPENDENT_CONTENT_BOUND_TOTAL_STRING_STRUCTURAL_ID_EXACTNESS_AND_6912_CASE_FALSIFICATION__ZERO_CREDIT",
 "brain_subject_commit":"704a60674e30de927bafaacecaf8a840d4632dbd",
 "exact_subject_blobs":EXPECTED,
 "unicode_codepoints_exhausted":unicode_codepoints,
 "surrogate_codepoints_exhausted":surrogate_codepoints,
 "v4_strict_utf8_counterexample_preserved":v4_surrogate_counterexample,
 "forced_total_token_collision_survival":True,
 "v2_exact_float_counterexample":counterexample,
 "nonproduction_falsification":{"populations":populations,"cases":cases,"all_pass":True},
 "production_or_terminal_cases_generated":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER",
   "SEPARATE_FAIL_CLOSED_ROOT3_AND_ACCEPTANCE_REDUCTION_REQUIRED"
 ],
}
Path("unknown_domain_v6_total_string_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True,ensure_ascii=True))

# PR synchronize trigger: verifier semantics unchanged.
