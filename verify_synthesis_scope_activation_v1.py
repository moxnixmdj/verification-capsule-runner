#!/usr/bin/env python3
import json,sys
from pathlib import Path

R=Path(__file__).resolve().parent
C=json.loads((R/"fixtures/synthesis_scope_certificate_v1.json").read_text())
A=json.loads((R/"fixtures/synthesis_scope_certificate_activation_v1.json").read_text())
T=json.loads((R/"fixtures/terminal_root_cause_state_for_synthesis_activation_v1.json").read_text())
errors=[]
PID="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"

if C.get("verified") is not True or C.get("independent") is not True:
    errors.append("CERT_NOT_VERIFIED_INDEPENDENT")
if C.get("basis")!="LOSSLESS_DECOMPOSITION":
    errors.append("CERT_BASIS")
if C.get("scope_relation")!="PROVEN_STRONGER":
    errors.append("CERT_SCOPE_RELATION")
if C.get("coverage_complete") is not True or C.get("coverage_relation")!="EXACT_UNION" or C.get("coverage_proof_verified") is not True:
    errors.append("CERT_COVERAGE")
children=C.get("children")
if not isinstance(children,list) or len(children)!=6:
    errors.append("CERT_CHILD_COUNT")
else:
    ids=[x.get("target_scope_id") for x in children if isinstance(x,dict)]
    if len(ids)!=len(set(ids)):
        errors.append("CERT_CHILD_DUPLICATE")
    for x in children:
        if not isinstance(x,dict): errors.append("CERT_CHILD_INVALID"); continue
        if x.get("verified") is not True or x.get("independent") is not True:
            errors.append("CERT_CHILD_NOT_VERIFIED")
        if x.get("basis")!="UNIVERSAL_FORMAL_SCOPE_PROOF":
            errors.append("CERT_CHILD_BASIS")
        if x.get("formal_completeness") is not True or x.get("all_admissible_target_inputs_proved") is not True:
            errors.append("CERT_CHILD_INCOMPLETE")

part=T.get("current_residual_root_partition") or {}
r2=list(part.get("root2_only") or [])
r3=list(part.get("root3_only") or [])
mixed=list(part.get("root2_and_root3") or [])
if PID not in mixed:
    errors.append("PID_NOT_MIXED_BEFORE")
if PID in r2:
    errors.append("PID_ALREADY_R2_ONLY")
if len(r2)!=15 or len(r3)!=7 or len(mixed)!=4:
    errors.append("BEFORE_COUNTS_DRIFT")
if part.get("unresolved_total")!=26:
    errors.append("UNRESOLVED_TOTAL_DRIFT")

after_r2=sorted(r2+[PID])
after_mixed=sorted(x for x in mixed if x!=PID)
if len(after_r2)!=16 or len(r3)!=7 or len(after_mixed)!=3:
    errors.append("DERIVED_AFTER_COUNTS")
if len(set(after_r2)|set(r3)|set(after_mixed))!=26:
    errors.append("DERIVED_UNRESOLVED_SET_SIZE")
root2_involved=len(after_r2)+len(after_mixed)
root3_involved=len(r3)+len(after_mixed)
if root2_involved!=19: errors.append("ROOT2_INVOLVED_COUNT")
if root3_involved!=10: errors.append("ROOT3_INVOLVED_COUNT")

decl=A.get("after_if_verified") or {}
expected={
"root2_only_count":16,"root3_only_count":7,"root2_and_root3_count":3,
"unresolved_total":26,"root2_involved_count":19,"root3_involved_count":10}
for k,v in expected.items():
    if decl.get(k)!=v: errors.append("DECLARED_AFTER_MISMATCH:"+k)

if set(A.get("remaining_root2_residuals") or []) != {
    "metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority"}:
    errors.append("ROOT2_RESIDUAL_SET")
for d in (C,A):
    for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        if d.get(k)!=0: errors.append("NONZERO_CREDIT:"+k)
    if d.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY_OVERCLAIM")

out={
"schema":"PROJECT_BRAIN_SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_INDEPENDENT_VERIFICATION_V1",
"status":"INDEPENDENT_PASS__RECLASSIFY_SYNTHESIS_ROOT2_AND_ROOT3_TO_ROOT2_ONLY__ROOT3_11_TO_10__ZERO_ACCEPTANCE_CREDIT" if not errors else "FAIL_CLOSED",
"pass":not errors,"errors":sorted(set(errors)),
"predicate_id":PID,
"before":{"root2_only":15,"root3_only":7,"root2_and_root3":4,"root3_involved":11},
"after":{"root2_only":16,"root3_only":7,"root2_and_root3":3,"root2_involved":19,"root3_involved":10,"unresolved_total":26},
"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
"new_reality_units_consumed":0,"incremental_spend_usd":0,
"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
}
print(json.dumps(out,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
