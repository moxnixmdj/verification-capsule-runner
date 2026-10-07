#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"opus55_finite_blackbox_literal_completeness_v1"
OUT=ROOT/"opus55_finite_blackbox_literal_completeness_v1_receipt.json"
EXPECTED={
 "SUBJECT.json":"3b8c53f1848b0365f8e68c4150b987aed700ccc5",
 "RUNTIME.py":"79850dee5f1d51bc4cf8b358e538c91192011f8b",
 "TEST.py":"fbd1e2029f7f7dcb97c6e1ec2a2734e0c17744d6",
}
def blob(path:Path)->str:
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for name,expected in EXPECTED.items():
 got=blob(SUB/name)
 assert got==expected,(name,got,expected)
doc=json.loads((SUB/"SUBJECT.json").read_text(encoding="utf-8"))
assert doc["status"].startswith("CANDIDATE__FINITE_BLACKBOX_EVIDENCE_CANNOT_BY_ITSELF_CERTIFY_W3")
assert doc["literal_target_application"]["w3_required_form"]=="(U_SUBSET_OR_EQUAL_D) AND UNIVERSAL_DOMINANCE_OVER_D"
assert doc["literal_target_application"]["deduction"]=="FINITE_BENCHMARK_OR_QUERY_TRANSCRIPTS_ALONE_DO_NOT_DISCHARGE_W3"
assert doc["accounting"]["acceptance_credit_delta"]==0
assert doc["fresh_reality_authority"] is False

spec=importlib.util.spec_from_file_location("finite_probe_nonidentifiability_certificate_v1",SUB/"RUNTIME.py")
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

cases=[
 [(0,)],
 [(0,),(0,),(1,),(2,)],
 [(Fraction(i,7),Fraction(i*i+3,11)) for i in range(17)],
 [tuple(i+j for j in range(5)) for i in range(9)],
]
receipts=[]
for probes in cases:
 out=mod.prove(probes)
 assert out["status"]=="PASS__FINITE_PROBES_CANNOT_UNIVERSALLY_IDENTIFY_UNRESTRICTED_FUNCTION_CLASS"
 assert Fraction(out["f1_at_witness"])>0
 assert all(v=="0" for v in out["f1_on_all_probes"])
 receipts.append({"dimension":out["dimension"],"probe_count":out["probe_count"],"witness":out["witness"],"f1_at_witness":out["f1_at_witness"]})

# Independent direct construction check, not merely trusting runtime status text.
def p(raw):
 return tuple(Fraction(str(x)) for x in raw)
def sq(a,b):
 return sum((x-y)*(x-y) for x,y in zip(a,b))
probes=[p((i,i*i+1)) for i in range(23)]
used=set(probes); k=0
while True:
 w=(Fraction(k+1),Fraction(k+2))
 if w not in used: break
 k+=3
def f1(x):
 z=Fraction(1)
 for q in probes: z*=sq(x,q)
 return z
assert all(f1(q)==0 for q in probes)
assert f1(w)>0

receipt={
 "schema":"PROJECT_BRAIN_OPUS55_FINITE_BLACKBOX_LITERAL_COMPLETENESS_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__EXACT_BLOBS_AND_CONSTRUCTIVE_NONIDENTIFIABILITY_RECOMPUTED__FINITE_BLACKBOX_ONLY_ROUTE_INSUFFICIENT_FOR_UNRESTRICTED_UNSEEN_DOMAIN__ZERO_CREDIT",
 "subject_blobs":EXPECTED,
 "checks":{
  "exact_subject_blob":True,
  "exact_runtime_blob":True,
  "exact_test_blob":True,
  "runtime_multiple_dimensions_recomputed":True,
  "independent_23_probe_construction_recomputed":True,
  "finite_probe_observational_equivalence_with_outside_disagreement":True,
  "subject_preserves_restricted_class_nonclaim":True,
 },
 "sample_receipts":receipts,
 "scope":"INFORMATION_THEORETIC_ROUTE_ELIMINATION_ONLY__NOT_OPUS_PERFORMANCE_OR_TARGET_COMPLETENESS_CREDIT",
 "authority":{"scheduling":False,"execution":False,"promotion":False,"fresh_reality":False},
 "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0},
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
