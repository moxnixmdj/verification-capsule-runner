import copy,hashlib,importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parent; F=R/"fixture"
def J(p,b=R): return json.loads((b/p).read_text())
def B(p):
 d=(R/p).read_bytes(); return hashlib.sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def D():
 p=lambda x:J(x,F)
 return [p("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
 p("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
 p("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
 p("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
 p("canonical/verification/CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
 p("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
 p("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
 p("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
 p("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")]
def main():
 e=[]; q=lambda c,x:e.append(x) if not c else None
 for p,v in J("EXPECTED_BRAIN_BLOBS.json").items(): q(B(p)==v["git_blob_sha"],"BLOB:"+p)
 s=importlib.util.spec_from_file_location("c",R/"candidate_runtime.py"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
 o=m.evaluate_repository(F); q(o.get("pass") is True,"LIVE")
 if o.get("pass"):
  q((o["live_world"]["proved_predicates"],o["live_world"]["unresolved_predicates"])==(11,27),"LIVE_COUNTS")
  q(o["action_refinement"]["primitive_acceptance_work_units"]==33,"LIVE_UNITS")
  q(len(o["first_resource_priority_work_unit_ids"])==16,"LIVE_PRIORITY")
  q(len(o["ownership_reconciliation_work_units"])==2,"LIVE_OWNERSHIP")
  q(not o["execution_authority"] and not o["promotion_authority"] and not o["fresh_reality_authority"],"AUTHORITY_LEAK")
  td=[x for x in o["acceptance_work_units"] if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in x["target_predicates"]]
  q(len(td)==1 and td[0]["mandatory_tool_discovery_v2_gate"] and td[0]["source_hints"][:2]==["MANDATORY_TOOL_DISCOVERY_V2_RETRIEVAL_GATE","NEW_ORTHOGONAL_SOURCE_EPOCH_ONLY"],"TD_GATE")
 d=copy.deepcopy(D()); d[4]["verified"]["unique_zero_reality_requirements"]=18
 q(not m.evaluate(*d)["pass"],"STALE_NOT_REJECTED")
 d=copy.deepcopy(D()); pid="AGENCY_MATCHED_SUCCESS_NONINFERIOR"
 c=next(x for x in d[1]["claims"] if x.get("predicate_id")==pid); c["state"]="PROVED"; c["scope_complete"]=True
 d[3]["live_world"]["proved_predicates"]=12; d[3]["live_world"]["unresolved_predicates"]=26
 d[4]["verified"]["proved_predicates"]=12; d[4]["verified"]["unresolved_predicates"]=26
 d[5]["targets"]=[x for x in d[5]["targets"] if x!=pid]; d[5]["implications"]=[x for x in d[5]["implications"] if x.get("then")!=[pid]]
 d[6]["result"].update(target_count=7,verified_rule_count=7,primitive_residual_fact_count=14,minimum_joint_residual_size=14)
 f=m.evaluate(*d); q(f.get("pass") is True,"FUTURE_REQUIRES_CODE_CHANGE")
 if f.get("pass"): q((f["live_world"]["proved_predicates"],f["live_world"]["unresolved_predicates"],f["live_world"]["matched_live_targets"],f["action_refinement"]["primitive_acceptance_work_units"])==(12,26,7,31),"FUTURE_COUNTS")
 print(json.dumps({"pass":not e,"errors":e,"new_reality_units_consumed":0,"incremental_spend_usd":0},indent=2)); return 0 if not e else 1
if __name__=="__main__": raise SystemExit(main())
