from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
C=ROOT/"capsules/composition_evidence_synthesis_bridge_v1/COMPOSITION_EVIDENCE_SYNTHESIS_SCOPE_COMPLETE_BRIDGE_V1.json"
M=ROOT/"capsules/composition_tool_discovery_bridge_v1/canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
P=ROOT/"fixtures/opus55_terminal_proof_protocols_v1.json"
B=ROOT/"fixtures/behavioral_contract_registry_v1.json"
S=ROOT/"fixtures/synthesis_scope_certificate_v1.json"

EXPECTED={
 str(C.relative_to(ROOT)):"000de52136566e33531e28d17973f0ced56f92aa",
 str(M.relative_to(ROOT)):"9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
 str(P.relative_to(ROOT)):"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 str(B.relative_to(ROOT)):"ee187f611a0e82b2de495ee377682f39bc31dd31",
 str(S.relative_to(ROOT)):"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
}
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def blob(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

errors=[]
for rel,expected in EXPECTED.items():
    p=ROOT/rel
    got=blob(p)
    if got!=expected: errors.append(f"BLOB_MISMATCH:{rel}:{got}")

c,m,p,b,s=map(load,(C,M,P,B,S))
rows=[x for x in m["interfaces"] if x.get("component_id")=="evidence synthesis"]
if len(rows)!=1: errors.append("FROZEN_COMPONENT_CARDINALITY")
else:
    r=rows[0]
    if r.get("interface_id")!="delegation+evidence synthesis+artifact production": errors.append("FROZEN_INTERFACE_DRIFT")
    if r.get("required_properties")!=["SCOPED_ACCEPTANCE_PROOF"]: errors.append("REQUIRED_PROPERTY_DRIFT")

comp=next((x for x in p["protocols"] if x.get("family")=="MULTI_CAPABILITY_COMPOSITION"),None)
syn=next((x for x in p["protocols"] if x.get("family")=="COMMUNICATION_AND_SYNTHESIS"),None)
if not comp or "delegation+evidence synthesis+artifact production" not in comp.get("task_dimensions",[]): errors.append("PARENT_DIMENSION_DRIFT")
if not comp or "Every isolated component used in the claim has its own scoped proof" not in comp.get("acceptance",""): errors.append("PARENT_SCOPE_PREDICATE_DRIFT")
expected_dims={
 "claim-to-source fidelity","required evidence coverage","uncertainty/disagreement preservation",
 "audience adaptation","format/style constraints","compression without decision-relevant loss",
}
if not syn or set(syn.get("task_dimensions",[]))!=expected_dims: errors.append("SYNTHESIS_SCOPE_DIMENSIONS_DRIFT")

fam=(b.get("family_to_residual_contracts") or {}).get("COMMUNICATION_AND_SYNTHESIS")
if fam!=["EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]: errors.append("FAMILY_TO_CONTRACT_MAPPING_DRIFT")
res=next((x for x in b.get("active_contracted_residuals",[]) if x.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"),None)
if not res: errors.append("SYNTHESIS_CONTRACT_MISSING")
else:
    if res.get("scope")!="Grounded evidence synthesis under audience and format constraints": errors.append("SYNTHESIS_CONTRACT_SCOPE_DRIFT")
    required=[
      ("inputs","Verified evidence units with provenance"),
      ("required_output_or_action","Select, organize and express the necessary evidence"),
      ("success_condition","required coverage is complete"),
      ("success_condition","compression does not delete decision-relevant evidence"),
    ]
    for field,frag in required:
        if frag not in str(res.get(field,"")): errors.append(f"CONTRACT_WITNESS_MISSING:{field}:{frag}")

if s.get("verified") is not True or s.get("independent") is not True: errors.append("SCOPE_CERT_NOT_INDEPENDENT_VERIFIED")
if s.get("scope_relation")!="PROVEN_STRONGER": errors.append("SCOPE_RELATION_NOT_STRONGER")
if s.get("coverage_complete") is not True or s.get("coverage_relation")!="EXACT_UNION": errors.append("SCOPE_NOT_EXACT_UNION")
children=s.get("children",[])
if len(children)!=6 or {x.get("target_scope_id","").split("/synthesis/")[-1] for x in children}!=expected_dims:
    errors.append("SCOPE_CHILDREN_NOT_EXACT_SIX")
if any(x.get("verified") is not True or x.get("independent") is not True or x.get("formal_completeness") is not True or x.get("all_admissible_target_inputs_proved") is not True for x in children):
    errors.append("SCOPE_CHILD_NOT_FORMALLY_COMPLETE")
if s.get("consequence",{}).get("root3_scope_relation_closed") is not True: errors.append("ROOT3_SCOPE_NOT_CLOSED")
if s.get("consequence",{}).get("predicate_remains_open_for_root2") is not True: errors.append("ROOT2_SEPARATION_LOST")

d=c.get("derivation",{})
if d.get("source_family_id")!="COMMUNICATION_AND_SYNTHESIS": errors.append("CANDIDATE_SOURCE_FAMILY_DRIFT")
if d.get("source_behavior_id")!="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001": errors.append("CANDIDATE_SOURCE_BEHAVIOR_DRIFT")
if d.get("source_scope_relation")!="PROVEN_STRONGER" or d.get("source_coverage_relation")!="EXACT_UNION" or d.get("source_coverage_complete") is not True:
    errors.append("CANDIDATE_SCOPE_CLAIM_DRIFT")
if set(c.get("exact_scope_guard",{}).get("included",[]))!=expected_dims: errors.append("CANDIDATE_SCOPE_GUARD_NOT_EXACT")
excluded=set(c.get("exact_scope_guard",{}).get("excluded",[]))
for x in ["DELEGATION_COMPONENT","ARTIFACT_PRODUCTION_COMPONENT","SYNTHESIS_MATCHED_QUALITY_OR_NONINFERIORITY","GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS","CROSS_CAPABILITY_STATE_HANDOFF_AND_ROLLBACK"]:
    if x not in excluded: errors.append("MISSING_EXCLUSION:"+x)

r=c.get("candidate_receipt",{})
if r.get("component_id")!="evidence synthesis" or r.get("interface_id")!="delegation+evidence synthesis+artifact production": errors.append("RECEIPT_BINDING_DRIFT")
if r.get("proved_properties")!=["SCOPED_ACCEPTANCE_PROOF"]: errors.append("RECEIPT_PROPERTY_DRIFT")
if r.get("verified") is not False or r.get("independent") is not False: errors.append("CANDIDATE_SELF_CERTIFICATION")
if r.get("contamination_clean") is not True or r.get("acceptance_scoped") is not True: errors.append("RECEIPT_SCOPE_FLAGS")
if r.get("binds_frozen_claim")!="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1": errors.append("RECEIPT_CLAIM_BINDING")
effect=c.get("expected_effect_after_independent_verification",{})
if effect.get("current_composition_scoped_proved_components_before")!=4 or effect.get("projected_scoped_proved_components_after")!=5 or effect.get("projected_open_components_after")!=7:
    errors.append("PROJECTED_COMPONENT_ARITHMETIC")
if effect.get("parent_component_dependency_predicate_closed") is not False or effect.get("parent_composition_predicate_closed") is not False:
    errors.append("PARENT_CREDIT_OVERCLAIM")
for k in ["acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    if c.get(k)!=0: errors.append("CREDIT_OVERCLAIM:"+k)
if c.get("fresh_reality_authority") is not False or c.get("execution_authority") is not False or c.get("promotion_authority") is not False:
    errors.append("AUTHORITY_OVERCLAIM")

out={
 "schema":"PROJECT_BRAIN_COMPOSITION_EVIDENCE_SYNTHESIS_BRIDGE_INDEPENDENT_VERIFIER_V1",
 "status":"INDEPENDENT_PASS__EVIDENCE_SYNTHESIS_COMPONENT_SCOPE_BRIDGE__ROOT3_COMPONENT_ELIGIBLE__ZERO_PARENT_OR_PERFORMANCE_CREDIT" if not errors else "FAIL_CLOSED",
 "pass":not errors,
 "errors":sorted(set(errors)),
 "verified_component":"evidence synthesis" if not errors else None,
 "verified_property":"SCOPED_ACCEPTANCE_PROOF" if not errors else None,
 "projected_scoped_components_after":5 if not errors else None,
 "projected_open_components_after":7 if not errors else None,
 "parent_composition_closed":False,
 "synthesis_root2_acceptance_closed":False,
 "new_reality_units_consumed":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
}
print(json.dumps(out,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
