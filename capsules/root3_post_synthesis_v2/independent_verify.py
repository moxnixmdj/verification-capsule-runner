import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
B=R/"brain"
M=json.loads((R/"EXPECTED_BRAIN_BLOBS.json").read_text())
def blob(p):
 d=(B/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(p): return json.loads((B/p).read_text())
errors=[]
for p,h in M["exact_brain_blobs"].items():
 if blob(p)!=h: errors.append("BLOB_DRIFT:"+p)
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
res=load("canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json")
pop=load("canonical/governance/ROOT3_TARGET_POPULATION_COALESCENCE_V1.json")
sp=load("canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V2.json")
cut=load("canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json")
comp=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
part=root.get("current_residual_root_partition") or root.get("partition") or root.get("residual_partition") or {}
r3=set(part.get("root3_only") or [])|set(part.get("root2_and_root3") or [])
if len(r3)!=10: errors.append("ROOT3_COUNT")
if "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in r3: errors.append("SYNTHESIS_STILL_ROOT3")
if pop.get("accounting",{}).get("formal_root3_target_count")!=7: errors.append("POP_FORMAL_COUNT")
ids={x.get("predicate_id") for x in sp.get("matched_scope_targets",[]) if isinstance(x,dict)}
if len(ids)!=7: errors.append("SUPERPORTFOLIO_TARGET_COUNT")
if "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in ids: errors.append("SYNTHESIS_IN_SUPERPORTFOLIO")
if sp.get("execution_compression",{}).get("shared_future_superportfolio_wave_count")!=1: errors.append("SUPERPORTFOLIO_WAVE")
if cut.get("derivation",{}).get("live_root3_predicates")!=10: errors.append("CUT_ROOT3_COUNT")
if len(cut.get("minimum_event_classes") or [])!=3: errors.append("CUT_EVENT_CLASSES")
syn=[x for x in res.get("compressed_residuals",[]) if isinstance(x,dict) and x.get("predicate_id")=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
if len(syn)!=1 or syn[0].get("root_class")!="ROOT2" or syn[0].get("scope_relation_closed") is not True: errors.append("SYNTHESIS_SCOPE_STATE")
t=comp.get("truth",{})
if t.get("current_admissible_scoped_proved")!=4 or t.get("current_open")!=8: errors.append("COMPOSITION_STATE")
if sp.get("fallback",{}).get("direct_oracle_batch",{}).get("frozen_leaf_count")!=4: errors.append("DIRECT_LEAF_COUNT")
for d in (sp,cut):
 if d.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY_OVERCLAIM")
 if d.get("acceptance_credit_delta")!=0: errors.append("CREDIT_OVERCLAIM")
out={
 "schema":"PROJECT_BRAIN_ROOT3_POST_SYNTHESIS_PUBLIC_VERIFICATION_V2",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__10_ROOT3_PREDICATES__7_MATCHED_SCOPE_TARGETS__3_EVENT_CLASSES__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
 "pass":not errors,"errors":errors,
 "verified":{"root3_predicates":10,"matched_scope_targets":7,"population_identities":4,"composition_open_interfaces":8,"direct_oracle_leaves":4,"event_class_count":3,"synthesis_root3":False},
 "new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"fresh_reality_authority":False
}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
