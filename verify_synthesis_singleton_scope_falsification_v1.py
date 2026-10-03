#!/usr/bin/env python3
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
B=ROOT/"capsules/synthesis_root3_scope_relation_v1/brain"
FILES={
 "candidate":B/"SYNTHESIS_SCOPE_RELATION_CERTIFICATE_V1.json",
 "registry":B/"BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
 "law":B/"BEHAVIORAL_CONTRACT_AND_SEMANTIC_PURGE_LAW_V1.md",
 "schema":B/"BEHAVIORAL_CONTRACT_SCHEMA_V1.json",
}
EXPECTED={
 "candidate":"bf1e43e31e4a20b3fa3cea51e295b41536f64b01",
 "registry":"ee187f611a0e82b2de495ee377682f39bc31dd31",
 "law":"5b70ed776f13194ea02d7df1d878a88386a48b61",
 "schema":"b173d8fc6e29df3cec3579954bb17c594308b151",
}
def blob(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

errors=[]
for k,p in FILES.items():
 if blob(p)!=EXPECTED[k]: errors.append("BLOB_DRIFT:"+k)

c=json.loads(FILES["candidate"].read_text())
r=json.loads(FILES["registry"].read_text())
s=json.loads(FILES["schema"].read_text())
law=FILES["law"].read_text()

proof=c.get("proof") or {}
if c.get("claimed_relation")!="PROVEN_STRONGER": errors.append("CANDIDATE_RELATION_CHANGED")
if proof.get("singleton_family_decomposition_required") is not True: errors.append("SINGLETON_PREMISE_MISSING")
if proof.get("family")!="COMMUNICATION_AND_SYNTHESIS": errors.append("FAMILY_CHANGED")
if proof.get("family_residual_contracts")!=["EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]: errors.append("CANDIDATE_CONTRACT_SET_CHANGED")
if (r.get("family_to_residual_contracts") or {}).get("COMMUNICATION_AND_SYNTHESIS")!=["EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]:
 errors.append("REGISTRY_MAPPING_CHANGED")
if s.get("family_labels")!="ACCOUNTING_LABEL_ONLY": errors.append("SCHEMA_FAMILY_LABEL_RULE_CHANGED")

required_law=[
 "The 19 Opus 5.5 capability families are acceptance/evaluation surfaces only.",
 "They MUST NOT be assumed to correspond to 19 internal modules.",
 "If it clusters multiple behaviors, split it until each leaf is independently testable.",
]
for lit in required_law:
 if lit not in law: errors.append("LAW_LITERAL_MISSING:"+lit)

# The rejected certificate cited no independent lossless family-decomposition theorem.
auth=c.get("authority") or {}
if any("decomposition" in str(k).lower() or "decomposition" in str(v).lower() for k,v in auth.items()):
 errors.append("CANDIDATE_AUTHORITY_NOW_CONTAINS_DECOMPOSITION_PROOF")

ok=not errors
out={
 "schema":"PROJECT_BRAIN_SYNTHESIS_SINGLETON_FAMILY_SCOPE_FALSIFICATION_INDEPENDENT_V1",
 "status":"INDEPENDENT_PASS__SINGLETON_FAMILY_MAPPING_NOT_ADMISSIBLE_AS_LOSSLESS_SCOPE_DECOMPOSITION__CANDIDATE_FALSIFIED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
 "pass":ok,
 "errors":errors,
 "rejected_candidate_blob":EXPECTED["candidate"],
 "canonical_law_blob":EXPECTED["law"],
 "canonical_schema_blob":EXPECTED["schema"],
 "falsified_inference":"SINGLETON_FAMILY_TO_RESIDUAL_CONTRACT_MAPPING=>TARGET_SCOPE_SUBSET",
 "required_for_reopening":"EXPLICIT_INDEPENDENT_LOSSLESS_OR_EXHAUSTIVE_FAMILY_TO_BEHAVIOR_DECOMPOSITION_CERTIFICATE",
 "scope_predicates_closed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "new_reality_units_consumed":0,
 "incremental_spend_usd":0,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if ok else 1)
