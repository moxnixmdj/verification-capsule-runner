#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
REPORT=ROOT/"pr468-broad-objective-routing-independent-report.json"
EXPECTED_ROLES=[
    "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION",
]

def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+rel)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def check(cond,label):
    if not cond:
        raise AssertionError(label)

def main():
    dec=load("canonical/runtime/bound_capabilities/broad_objective_decompose.py","independent_broad_dec")
    grounding=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","independent_grounding")
    fresh=[
        (
            "MATERIALS_MULTICLAUSE",
            "Evaluate whether ceramic fatigue strength differs between two thermal regimes. "
            "Use authoritative primary technical evidence and a real executable check. "
            "Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, "
            "state material scope limitations, independently verify the consequential result, and preserve provenance."
        ),
        (
            "TELEMETRY_MULTICLAUSE",
            "Investigate whether satellite telemetry latency is lower in operating mode Alpha than operating mode Beta. "
            "Use authoritative primary technical evidence and an executable check. "
            "Autonomously discover and verify relevant documentation, choose and run a zero-cost verification method, "
            "identify scope limitations, independently verify the consequential result, and preserve provenance."
        ),
        (
            "DATABASE_MULTICLAUSE",
            "Quantify whether database checkpoint duration changed between two storage configurations. "
            "Use authoritative primary technical evidence and a real executable check. "
            "Autonomously discover and verify relevant documentation, choose and run a zero-cost verification method, "
            "identify interpretation limitations, independently verify the consequential result, and preserve provenance."
        ),
    ]
    report={"schema":"PROJECT_BRAIN_PR468_INDEPENDENT_QUALIFICATION_V1","fresh_cases":[],"negative_cases":[],"model_dependency_count":0,"incremental_spend_usd":0}
    for cid,objective in fresh:
        d=dec.decompose(objective)
        check(d.get("status")=="DECOMPOSED",cid+": direct decomposition")
        check([r.get("role") for r in d.get("roles",[])]==EXPECTED_ROLES,cid+": role graph")
        check(d.get("invented_source_urls")==[],cid+": invented URLs")
        check(d.get("invented_facts")==[],cid+": invented facts")
        g=grounding.ground(objective,{})
        check(len(g.get("clauses",[]))>1,cid+": multiclause")
        check(g.get("grounded_clause_count")==0,cid+": zero grounded")
        check(len(g.get("unresolved_clause_indexes",[]))==len(g.get("clauses",[])),cid+": all unresolved")
        check(g.get("broad_objective_decomposition_available") is True,cid+": route activated")
        check((g.get("broad_objective_decomposition") or {}).get("status")=="DECOMPOSED",cid+": routed decomposition")
        check(g.get("model_dependency_count")==0,cid+": model free")
        report["fresh_cases"].append({"id":cid,"status":"PASS","clause_count":len(g["clauses"]),"question_shape":d.get("question_shape")})

    negatives=[
        ("CONCRETE_PYTHON_COMMAND","Assess whether two measurements differ. Run python verify_values.py","OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"),
        ("CONCRETE_SHELL_COMMAND","Determine whether two measurements differ. Execute bash verify_values.sh","OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"),
        ("SUPPLIED_URL_RECIPE","Assess whether two values differ using https://example.com/data and extract JSON path value","OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"),
    ]
    for cid,objective,reason in negatives:
        d=dec.decompose(objective)
        check(d.get("status")=="UNSUPPORTED",cid+": must reject")
        check(d.get("reason")==reason,cid+": reject reason")
        report["negative_cases"].append({"id":cid,"status":"PASS","reason":d.get("reason")})

    partial=(
        "Assess whether checksum Alpha differs from checksum Beta. "
        "Preserve provenance and independently verify the result."
    )
    registry={
        "checksum.compare.stdlib":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "provides":["checksum comparison"],
            "requires":[],
            "keywords":["checksum alpha beta compare"],
            "source":{"type":"stdlib"},
        }
    }
    pg=grounding.ground(partial,registry)
    check(pg.get("grounded_clause_count",0)>=1,"partial grounding must ground")
    check(pg.get("broad_objective_decomposition_available") is False,"partial grounding must not hijack whole goal")
    check(pg.get("whole_goal_external_discovery_forbidden_if_any_bound_grounding") is True,"partial grounding guard")
    report["negative_cases"].append({"id":"PARTIAL_GROUNDING_NO_WHOLE_GOAL_REINTERPRETATION","status":"PASS","grounded_clause_count":pg.get("grounded_clause_count")})

    action=grounding.ground("Create output.json with one record",{})
    check(action.get("broad_objective_decomposition_available") is False,"ordinary action must remain non-broad")
    report["negative_cases"].append({"id":"NON_BROAD_ACTION","status":"PASS"})

    report["status"]="PASS"
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
