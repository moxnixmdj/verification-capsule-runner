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
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

got={rel:blob(ROOT/rel) for rel in EXPECTED}
assert got==EXPECTED,{"expected":EXPECTED,"got":got}

# Independent codec-domain audit. The V4 hole was not numeric; arbitrary Python
# strings could reach strict UTF-8 helpers. V5 must first map every accepted str
# through surrogatepass bytes and injective lowercase hex.
prefix="UDIRV5-BEACON-HEX|"
surrogate_encodings=set()
for cp in range(0xD800,0xE000):
 s="A"*16+chr(cp)
 out=g5._canonical_beacon(s)
 assert out.startswith(prefix) and out.isascii()
 raw=bytes.fromhex(out[len(prefix):])
 assert raw.decode("utf-8","surrogatepass")==s
 surrogate_encodings.add(out)
assert len(surrogate_encodings)==0x800

normal_samples=[
 "A"*16,
 "A"*16+"\x00",
 "A"*16+"Ω",
 "A"*16+"😀",
 "A"*16+"e\u0301",
 "界"*16,
]
normal_encodings=set()
for s in normal_samples:
 out=g5._canonical_beacon(s)
 raw=bytes.fromhex(out[len(prefix):])
 assert raw.decode("utf-8","surrogatepass")==s
 normal_encodings.add(out)
assert len(normal_encodings)==len(normal_samples)
assert surrogate_encodings.isdisjoint(normal_encodings)
assert g5._secret_bytes_total("S"*31+"\ud800").decode("utf-8","surrogatepass")=="S"*31+"\ud800"
assert g5._secret_bytes_total("\udfff"+"T"*31).decode("utf-8","surrogatepass")=="\udfff"+"T"*31
assert g5._secret_bytes_total(b"U"*32)==b"U"*32

# Content-bound implementation audit: no legacy strict encode may see the raw
# accepted beacon before canonicalization.
src="".join(inspect.getsource(g5._canonical_beacon).split())
assert '.encode("utf-8","surrogatepass")' in src
assert 'raw.hex()' in src
assert "return\"UDIRV5-BEACON-HEX|\"+raw.hex()" in src

def run_packet(packet):
 rows=[]
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
  ex=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
  assert ex["scorer_result"]["pass"] is True, json.dumps({
   "case_id":visible.get("case_id"),
   "errors":ex["scorer_result"].get("errors"),
  },sort_keys=True)
  rows.append(ex["scorer_result"])
 assert scorer.aggregate(rows)["all_27_cases_pass"] is True
 return len(rows)

# Strong conjunction falsifier: force every legacy opaque token to collide while
# simultaneously using lone surrogates on both accepted string surfaces.
orig=g1._token
try:
 g1._token=lambda *args,**kwargs:"COLLISION"
 forced=g5._generate(
  beacon="A"*16+"\ud800",
  evaluator_secret="S"*31+"\udfff",
  namespace="V6-INDEPENDENT-COLLISION",
 )
 assert forced["case_count"]==27
 assert len({x["case_id"] for x in forced["visible_cases"]})==27
 forced_cases=run_packet(forced)
finally:
 g1._token=orig

# Find a reachable V2 exact-float failure under the V5 wrapper and require V3 to
# repair the exact same hidden record. No production entrypoint is used.
counterexample=None
for k in range(256):
 packet=g5._generate(
  beacon=f"V6-FLOAT-{k:04d}-"+"B"*16,
  evaluator_secret=hashlib.sha256(f"v6-secret-{k}".encode()).digest(),
  namespace=f"V6FLOAT{k}",
 )
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
  if hidden["leaf_id"]!=g1.TRANSFER or hidden.get("primitive_family")!="COMPOSITIONAL_REWRITE":
   continue
  bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
  if bad["scorer_result"]["pass"] is False and "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"].get("errors",[]):
   good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
   assert good["scorer_result"]["pass"] is True
   assert good["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
   counterexample={
    "population":k,
    "case_id":visible["case_id"],
    "v2":bad["candidate_terminal_action"].get("terminal_consequence"),
    "gold":hidden["gold_terminal_consequence"],
   }
   break
 if counterexample:
  break
assert counterexample is not None,"V2_EXACT_FLOAT_COUNTEREXAMPLE_NOT_FOUND"

# Cross-product adversarial string sweep, still synthetic/nonproduction.
beacons=[
 "Q"*16+"\ud800",
 "\udfff"+"R"*16,
 "S"*16+"😀",
 "Ω"*16,
 "\x00"+"T"*16,
 "界"*16,
]
secrets=[
 "K"*31+"\ud800",
 "\udfff"+"L"*31,
 "M"*32+"😀",
 "Ω"*32,
 b"N"*32,
 b"\x00"*32,
]
populations=0
cases=0
for i,b in enumerate(beacons):
 for j,s in enumerate(secrets):
  packet=g5._generate(beacon=b,evaluator_secret=s,namespace=f"V6X{i}_{j}")
  cases+=run_packet(packet)
  populations+=1
assert populations==36 and cases==972

# Compare the independently attacked subject with the proposed universal theorem
# only after the attack surface above has passed.
theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert theorem["string_interface_totality"]["utf8_surrogatepass_total"] is True
assert theorem["identifier_totality_proof"]["token_collision_resistance_required_for_semantic_distinctness"] is False
assert theorem["transfer_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__EXACT_BYTES__TOTAL_STRING_SURROGATE_DOMAIN__FORCED_IDENTIFIER_COLLISION__EXACT_FLOAT_REPAIR__ZERO_CREDIT",
 "exact_subject_blobs":EXPECTED,
 "surrogate_codepoints_exhausted":2048,
 "normal_unicode_roundtrip_samples":len(normal_samples),
 "forced_all_token_collision_cases":forced_cases,
 "v2_exact_float_counterexample_repaired":counterexample,
 "adversarial_string_cross_product":{"populations":populations,"cases":cases,"all_pass":True},
 "production_or_terminal_cases_generated":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
  "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_BOUND_EVALUATOR_CONTRACT",
  "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER_ALONE",
  "SEPARATE_ROOT3_SCOPE_AND_ACCEPTANCE_REDUCTION_REQUIRED"
 ],
}
Path("unknown_domain_v6_independent_verification_v1.json").write_text(
 json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
