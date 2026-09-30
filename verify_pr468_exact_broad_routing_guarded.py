#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"pr468-broad-routing-independent-report.json"
EXPECTED={
  "broad_objective_decompose.py":"1efaec4ba51ecb5c40072b3190853f4de89d8f77",
  "plain_goal_bound_grounding.py":"25738e959dec0be46058e4bd7720fb8ed1b599bb",
  "test_broad_objective_semantic_decomposition.py":"cf7c5ceab23724ec0d6b5c7ff5462c591da64804",
}

def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def require(cond,label,detail=None):
    if not cond:
        raise AssertionError(label+((": "+repr(detail)) if detail is not None else ""))

def main():
    require(blob_sha(CAP/"broad_objective_decompose.py")==EXPECTED["broad_objective_decompose.py"],"broad byte mismatch")
    require(blob_sha(CAP/"plain_goal_bound_grounding.py")==EXPECTED["plain_goal_bound_grounding.py"],"grounding byte mismatch")
    require(blob_sha(ROOT/"canonical/tests/test_broad_objective_semantic_decomposition.py")==EXPECTED["test_broad_objective_semantic_decomposition.py"],"test byte mismatch")
    dec=load(CAP/"broad_objective_decompose.py","pr468_independent_dec")
    grounding=load(CAP/"plain_goal_bound_grounding.py","pr468_independent_grounding")
    cases=[]

    fresh=[
      ("materials",
       "Assess whether the maximum allowable thermal gradient in a reference material is greater than its ordinary operating gradient. "
       "Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify the relevant technical source, "
       "determine how to extract and interpret the required limits, choose and run a zero-cost verification method, identify material scope or "
       "interpretation limitations, independently verify the consequential result, and produce a decision-quality answer with provenance."),
      ("database",
       "Determine whether a database engine's maximum supported page size is greater than its default page size. "
       "Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify relevant sources, "
       "choose and run a zero-cost verification method, identify scope limitations, independently verify the consequential result, "
       "and produce a decision-quality answer with provenance."),
      ("energy",
       "Evaluate whether a grid-scale battery's documented upper operating temperature is greater than its ordinary reference temperature. "
       "Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify relevant sources, "
       "choose and run a zero-cost verification method, identify interpretation limitations, independently verify the consequential result, "
       "and produce a decision-quality answer.")
    ]
    for label,goal in fresh:
        d=dec.decompose(goal)
        require(d.get("status")=="DECOMPOSED",label+" decomposition",d)
        g=grounding.ground(goal,{})
        require(len(g.get("clauses") or [])>1,label+" multiclause",g)
        require(g.get("grounded_clause_count")==0,label+" zero grounded",g)
        require(len(g.get("unresolved_clause_indexes") or [])==len(g.get("clauses") or []),label+" all unresolved",g)
        require((g.get("broad_objective_decomposition") or {}).get("status")=="DECOMPOSED",label+" broad route",g)
        require(g.get("model_dependency_count")==0,label+" model dependency",g)
        cases.append({"id":"FRESH_"+label.upper(),"status":"PASS","clause_count":len(g["clauses"])})

    generic=dec.decompose(
      "Assess whether a property differs between two regimes. Choose and run a zero-cost verification method."
    )
    require(generic.get("status")=="DECOMPOSED","generic run-method wording must remain research",generic)
    cases.append({"id":"GENERIC_RUN_METHOD_NOT_COMMAND","status":"PASS"})

    for command in [
      "Assess whether two measured values differ. Run python verify_values.py",
      "Assess whether two measured values differ. Execute bash ./verify.sh",
      "Determine whether values differ using https://example.com/data and extract JSON path value",
    ]:
        d=dec.decompose(command)
        require(d.get("status")=="UNSUPPORTED","concrete recipe rejected",d)
        require(d.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE","recipe reason",d)
    cases.append({"id":"CONCRETE_RECIPES_FAIL_CLOSED","status":"PASS"})

    nonresearch=dec.decompose("Create canonical/astra_runtime/tmp/result.json with one record")
    require(nonresearch.get("status")=="UNSUPPORTED","non-research action rejected",nonresearch)
    cases.append({"id":"NON_RESEARCH_ACTION_NOT_BROADENED","status":"PASS"})

    partial_goal=(
      "Create a barcode artifact. "
      "Assess whether a protocol limit differs from its default using authoritative primary technical evidence."
    )
    registry={
      "artifact.barcode.synthetic":{
        "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
        "provides":["artifact.barcode.create"],"requires":[],
        "keywords":["barcode","artifact","create"],"source":{"type":"independent_fixture"},
        "action_template":{"type":"invoke_capability","args":{}}
      }
    }
    g=grounding.ground(partial_goal,registry)
    require(g.get("grounded_clause_count",0)>0,"partial grounding exists",g)
    require(g.get("broad_objective_decomposition") is None,"partial grounding must suppress whole-goal broad fallback",g)
    require(g.get("whole_goal_external_discovery_forbidden_if_any_bound_grounding") is True,"external discovery guard",g)
    cases.append({"id":"PARTIAL_GROUNDING_UNCHANGED","status":"PASS"})

    report={
      "schema":"PROJECT_BRAIN_PR468_BROAD_ROUTING_INDEPENDENT_QUALIFICATION_V2",
      "status":"PASS","candidate_blobs":EXPECTED,"cases":cases,
      "parent_task_execution":False,"spent_http2_task_replayed":False,
      "model_dependency_count":0,"incremental_spend_usd":0
    }
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        REPORT.write_text(json.dumps({
          "schema":"PROJECT_BRAIN_PR468_BROAD_ROUTING_INDEPENDENT_QUALIFICATION_V2",
          "status":"FAIL","error_class":type(exc).__name__,"error":str(exc),
          "parent_task_execution":False,"spent_http2_task_replayed":False,
          "model_dependency_count":0,"incremental_spend_usd":0
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise
