#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path

R=Path(__file__).resolve().parent
C=json.loads((R/"fixtures/synthesis_lossless_scope_decomposition_v1.json").read_text())
P=json.loads((R/"fixtures/opus55_terminal_proof_protocols_v1.json").read_text())
B=json.loads((R/"fixtures/behavioral_contract_registry_v1.json").read_text())
S=json.loads((R/"fixtures/opus55_synthesis_implication_residual_input_v2.json").read_text())
A=json.loads((R/"fixtures/synthesis_overlay_v3_rebind_verification.json").read_text())
errors=[]

expected={
"fixtures/synthesis_lossless_scope_decomposition_v1.json":"72f31ed22331be258e8762bedf0f0df3596af8d7",
"fixtures/opus55_terminal_proof_protocols_v1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
"fixtures/behavioral_contract_registry_v1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
"fixtures/opus55_synthesis_implication_residual_input_v2.json":"4e5b944c86b8745083cc9d97fe186aa4b1322747",
"fixtures/synthesis_overlay_v3_rebind_verification.json":"1a67bc568944212c4d235a463c8bd7bea21b3993",
}
for p,h in expected.items():
 got=subprocess.check_output(["git","hash-object",p],text=True).strip()
 if got!=h: errors.append("BLOB_MISMATCH:"+p)

prow=next((x for x in P["protocols"] if x.get("family")=="COMMUNICATION_AND_SYNTHESIS"),None)
brow=next((x for x in B["active_contracted_residuals"] if x.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"),None)
dims=set(prow.get("task_dimensions",[]) if prow else [])
expected_dims={
"claim-to-source fidelity","required evidence coverage","uncertainty/disagreement preservation",
"audience adaptation","format/style constraints","compression without decision-relevant loss"}
if dims!=expected_dims: errors.append("PROTOCOL_DIMENSIONS_NOT_EXACT")
bindings=C.get("dimension_bindings",[])
if len(bindings)!=6: errors.append("BINDING_COUNT")
seen=set()
for row in bindings:
 d=row.get("target_dimension")
 if d in seen: errors.append("DUPLICATE_DIMENSION:"+str(d))
 seen.add(d)
 if d not in expected_dims: errors.append("UNKNOWN_DIMENSION:"+str(d))
 ws=row.get("contract_witnesses",[])
 if not ws: errors.append("NO_WITNESS:"+str(d))
 for w in ws:
  field=w.get("field"); fragment=w.get("fragment")
  actual=(brow or {}).get(field)
  if not isinstance(actual,str) or not isinstance(fragment,str) or fragment not in actual:
   errors.append("BAD_WITNESS:"+str(d)+":"+str(field))
if seen!=expected_dims: errors.append("DIMENSION_COVERAGE_OPEN")

# Independently require the behavioral contract to carry the six semantic obligations.
required_fragments={
"inputs":["Verified evidence units with provenance","user objective/audience","output constraints","required claims"],
"required_output_or_action":["required claims are supported","material uncertainty/disagreement is preserved","irrelevant detail is omitted"],
"success_condition":["no unsupported material claims","required coverage is complete","audience/format constraints pass","compression does not delete decision-relevant evidence"],
}
for field,frags in required_fragments.items():
 actual=(brow or {}).get(field,"")
 for frag in frags:
  if frag not in actual: errors.append("INDEPENDENT_CONTRACT_REQUIREMENT_MISSING:"+field+":"+frag)

target=(S.get("algebra_input") or {}).get("target") or {}
witness=(S.get("algebra_input") or {}).get("witness") or {}
dim_atoms={
"dimension:claim_to_source_fidelity","dimension:required_evidence_coverage",
"dimension:uncertainty_and_disagreement_preservation","dimension:audience_adaptation",
"dimension:format_and_style_constraints","dimension:compression_without_decision_relevant_loss"}
if not dim_atoms.issubset(set(target.get("required_atoms",[]))): errors.append("TARGET_DIMENSION_ATOMS_DRIFT")
if not dim_atoms.issubset(set(witness.get("proved_atoms",[]))): errors.append("WITNESS_DIMENSION_ATOMS_OPEN")
if ((S.get("expected_residual") or {}).get("missing_scope_relation") is not True): errors.append("INPUT_SCOPE_RELATION_NOT_OPEN")
v=A.get("verified",{})
if v.get("transported_proved_atom_count")!=7: errors.append("SEVEN_ATOM_STATE_DRIFT")
if v.get("missing_scope_relation") is not True: errors.append("PRIOR_SCOPE_STATE_DRIFT")

dec=C.get("decomposition_claim",{})
if dec.get("coverage_complete") is not True or dec.get("coverage_relation")!="EXACT_UNION": errors.append("DECOMPOSITION_NOT_LOSSLESS")
if C.get("scope_relation")!="PROVEN_STRONGER": errors.append("SCOPE_RELATION_TYPE")
if C.get("acceptance_credit_delta")!=0 or C.get("family_credit_delta")!=0 or C.get("capability_credit_delta")!=0 or C.get("ownership_credit_delta")!=0:
 errors.append("CREDIT_OVERCLAIM")
if C.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY_OVERCLAIM")

out={
"schema":"PROJECT_BRAIN_SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_INDEPENDENT_VERIFICATION_V1",
"status":"INDEPENDENT_PASS__LOSSLESS_SIX_DIMENSION_SCOPE_RELATION__ROOT3_SCOPE_RELATION_ELIGIBLE__ZERO_PERFORMANCE_CREDIT" if not errors else "FAIL_CLOSED",
"pass":not errors,
"errors":sorted(set(errors)),
"target_dimension_count":6 if not errors else None,
"bound_dimension_count":6 if not errors else None,
"scope_relation":"PROVEN_STRONGER" if not errors else None,
"root3_scope_relation_eligible":not errors,
"remaining_root2_residuals":["metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority"] if not errors else [],
"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
"new_reality_units_consumed":0,"incremental_spend_usd":0,"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
}
print(json.dumps(out,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
