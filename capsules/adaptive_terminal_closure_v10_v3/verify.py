import copy, hashlib, importlib.util, json
from pathlib import Path

R=Path(__file__).resolve().parent
F=R/"fixture"

def J(p,b=R):
    return json.loads((b/p).read_text(encoding="utf-8"))

def B(p):
    d=(R/p).read_bytes()
    return hashlib.sha1(f"blob {len(d)}\0".encode()+d).hexdigest()

def D():
    p=lambda x:J(x,F)
    return [
        p("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        p("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        p("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        p("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
        p("canonical/verification/CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        p("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        p("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
        p("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        p("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        p("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
    ]

def main():
    errors=[]
    q=lambda cond,msg: errors.append(msg) if not cond else None
    exp=J("EXPECTED_BRAIN_BLOBS.json")
    for p,v in exp.items():
        q(B(p)==v["git_blob_sha"],"BLOB:"+p)

    activation=J("candidate_activation.json")
    q(activation.get("fresh_reality_authority") is False,"ACTIVATION_FRESH_REALITY")
    q(activation.get("execution_authority") is False,"ACTIVATION_EXECUTION")
    q(activation.get("promotion_authority") is False,"ACTIVATION_PROMOTION")

    spec=importlib.util.spec_from_file_location("candidate",R/"candidate_runtime.py")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

    docs=D()
    out=m.evaluate(*docs)
    q(out.get("pass") is True,"LIVE")
    if out.get("pass"):
        q((out["live_world"]["proved_predicates"],out["live_world"]["unresolved_predicates"])==(11,27),"LIVE_COUNTS")
        q(out["live_world"]["nondominated_certificates"]==16,"CERTS")
        q(out["live_world"]["verified_zero_reality_requirements"]==19,"REQS")
        q(out["live_world"]["matched_primitive_child_facts"]==16,"MATCHED_CHILDREN")
        q(out["action_refinement"]["primitive_acceptance_work_units"]==33,"WORK_UNITS")
        q(len(out["first_resource_priority_work_unit_ids"])==16,"PRIORITY_16")
        q(len(out["ownership_reconciliation_work_units"])==2,"OWNERSHIP_2")
        td=[x for x in out["acceptance_work_units"] if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in x["target_predicates"]]
        q(len(td)==1,"TD_COUNT")
        if len(td)==1:
            q(td[0].get("mandatory_tool_discovery_v3_gate") is True,"TD_V3_GATE")
            q(td[0].get("source_hints",[])[:1]==["MANDATORY_TOOL_DISCOVERY_V3_OVER_VERIFIED_V2_BASE_RETRIEVAL_GATE"],"TD_V3_HINT")
        q(not out["execution_authority"] and not out["promotion_authority"] and not out["fresh_reality_authority"],"AUTHORITY_LEAK")

    stale=copy.deepcopy(docs)
    stale[-1]["status"]="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V9_CURRENT"
    s=m.evaluate(*stale)
    q(s.get("pass") is False and "SCHEDULING_AUTHORITY_NOT_CURRENT_V10_INDEPENDENT_PASS" in s.get("errors",[]),"STALE_V9_NOT_REJECTED")

    prev3=copy.deepcopy(docs)
    prev3[-1]["mandatory_tool_discovery_retrieval"]["pre_v3_epoch_exhaustion_allowed"]=True
    p=m.evaluate(*prev3)
    q(p.get("pass") is False and "SCHEDULING_AUTHORITY_PRE_V3_EXHAUSTION_NOT_FORBIDDEN" in p.get("errors",[]),"PRE_V3_NOT_REJECTED")

    future=copy.deepcopy(docs)
    pid="COMPOSITION_COMPONENT_SCOPED_PROOFS"
    claim=next(x for x in future[1]["claims"] if x.get("predicate_id")==pid)
    claim["state"]="PROVED"; claim["scope_complete"]=True
    future[3]["live_world"]["proved_predicates"]=12; future[3]["live_world"]["unresolved_predicates"]=26
    future[4]["verified"]["proved_predicates"]=12; future[4]["verified"]["unresolved_predicates"]=26
    future[-1]["live_world"]["proved_predicates"]=12; future[-1]["live_world"]["unresolved_predicates"]=26
    f=m.evaluate(*future)
    q(f.get("pass") is True,"FUTURE_REQUIRES_CODE_CHANGE")
    if f.get("pass"):
        q((f["live_world"]["proved_predicates"],f["live_world"]["unresolved_predicates"])==(12,26),"FUTURE_COUNTS")

    print(json.dumps({"pass":not errors,"errors":errors,"new_reality_units_consumed":0,"incremental_spend_usd":0},indent=2))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
