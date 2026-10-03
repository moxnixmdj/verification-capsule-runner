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
a=load("canonical/governance/ROOT3_UNIVERSAL_SCOPE_CLOSURE_ACTIVATION_V1.json")
c=load("canonical/governance/ROOT3_TARGET_POPULATION_COALESCENCE_V1.json")
sp=load("canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json")
sat=load("canonical/governance/CURRENT_ROOT3_ZERO_REALITY_STRONGER_PROOF_SATURATION_V1.json")
res=load("canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json")
comp=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
cut=load("canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json")
if a.get("current_truth",{}).get("live_root3_predicates")!=11: errors.append("ROOT3_COUNT")
if c.get("accounting",{}).get("population_group_count")!=4: errors.append("POPULATION_GROUP_COUNT")
m=sat.get("current_matched_surface_result",{})
if m.get("pair_count")!=96 or m.get("direct_reuse_closures")!=0: errors.append("SATURATION")
ec=sp.get("execution_compression",{})
if ec.get("matched_scope_target_count")!=8 or ec.get("shared_future_superportfolio_wave_count")!=1: errors.append("SUPERPORTFOLIO")
by={x.get("predicate_id"):x for x in res.get("compressed_residuals",[]) if isinstance(x,dict)}
if by.get("FINANCE_UNCOVERED_SCOPE_AUDIT",{}).get("current_residual")!="TWO_FROZEN_DIRECT_ORACLE_LEAVES": errors.append("FINANCE_LEAVES")
if not str(by.get("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",{}).get("current_residual","")).startswith("TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES"): errors.append("UNKNOWN_LEAVES")
if by.get("SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",{}).get("current_residual",{}).get("missing_scope_relation") is not True: errors.append("SYNTHESIS_SCOPE")
t=comp.get("truth",{})
if t.get("current_admissible_scoped_proved")!=4 or t.get("current_open")!=8: errors.append("COMPOSITION")
if cut.get("minimum_event_classes")!=["NEW_SCOPE_CERTIFICATE_EVENT","UPSTREAM_SCOPE_RECEIPT_EVENT","ROOT3_FRESH_REALITY_EVENT"]: errors.append("CUT_EVENT_CLASSES")
if cut.get("current_consequence")!="NO_NONDOMINATED_ROOT3_EXECUTION_IS_CURRENTLY_AUTHORIZED_OR_INFORMATION_POSITIVE_UNDER_BOUND_EVIDENCE__WAIT_FOR_A_RESUME_EVENT": errors.append("CUT_CONSEQUENCE")
out={"schema":"PROJECT_BRAIN_ROOT3_MINIMUM_ACTION_CUT_PUBLIC_VERIFICATION_V1","status":"INDEPENDENT_PUBLIC_RUNNER_PASS__11_ROOT3_PREDICATES_TO_3_EVENT_CLASSES__ZERO_CURRENT_RUNNABLE_ACTIONS__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"verified":{"live_root3_predicates":11,"formal_population_identities":4,"matched_scope_targets_one_wave":8,"composition_open_interfaces":8,"direct_oracle_leaves":4,"event_class_count":3,"currently_runnable_event_count":0},"new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"fresh_reality_authority":False}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
