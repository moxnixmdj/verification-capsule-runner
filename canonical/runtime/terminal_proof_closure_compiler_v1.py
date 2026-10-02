"""Fail-closed compiler for Project Brain terminal proof closure."""
from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any, Mapping
import argparse, json
from pathlib import Path

SCHEMA="PROJECT_BRAIN_TERMINAL_PROOF_CLOSURE_COMPILER_V1"
BASIS_SCHEMA="PROJECT_BRAIN_ACTIVE_TERMINAL_PROOF_BASIS_V1"
INDEX_SCHEMA="PROJECT_BRAIN_TERMINAL_PROOF_EVIDENCE_INDEX_V1"

def mechanical_gate(blocker:str)->str|None:
    if blocker=="SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS":
        return "SCOPE_GATE_V2"
    if blocker.startswith("POST_FREEZE_") and ("POPULATION" in blocker or "ACCEPTANCE" in blocker or "BINDING" in blocker):
        return "POST_FREEZE_BINDING"
    return None

def _strings(v:Any,name:str)->list[str]:
    if not isinstance(v,list) or any(not isinstance(x,str) or not x for x in v):
        raise ValueError(name)
    return list(v)

def compile_frontier(basis:Mapping[str,Any], index:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    if basis.get("schema")!=BASIS_SCHEMA: errors.append("BASIS_SCHEMA_INVALID")
    if index.get("schema")!=INDEX_SCHEMA: errors.append("INDEX_SCHEMA_INVALID")
    rows=basis.get("contracts")
    evidence=index.get("contracts")
    if not isinstance(rows,list):
        errors.append("BASIS_CONTRACTS_INVALID"); rows=[]
    if not isinstance(evidence,dict):
        errors.append("EVIDENCE_INDEX_CONTRACTS_INVALID"); evidence={}
    ids=[r.get("behavior_id") for r in rows if isinstance(r,Mapping) and isinstance(r.get("behavior_id"),str)]
    if len(ids)!=len(rows): errors.append("BASIS_ROW_INVALID")
    if len(ids)!=len(set(ids)): errors.append("BASIS_DUPLICATE_BEHAVIOR_ID")
    if basis.get("active_contract_count")!=len(set(ids)): errors.append("BASIS_ACTIVE_COUNT_MISMATCH")
    compiled=[]; mech_hist=Counter(); semantic_dupes=defaultdict(list)
    for row in rows:
        if not isinstance(row,Mapping) or not isinstance(row.get("behavior_id"),str): continue
        bid=row["behavior_id"]; blockers=row.get("blockers")
        if not isinstance(blockers,list) or any(not isinstance(x,str) or not x for x in blockers):
            errors.append("BLOCKERS_INVALID:"+bid); blockers=[]
        semantic=[]; mechanical=[]
        for b in blockers:
            gate=mechanical_gate(b)
            if gate is None: semantic.append("BASIS::"+b)
            else:
                mechanical.append({"gate":gate,"source":"BASIS","detail":b}); mech_hist[gate]+=1
        ev=evidence.get(bid); inspection_complete=False; inspected=[]
        if isinstance(ev,Mapping):
            inspection_complete=ev.get("inspection_complete") is True
            sources=ev.get("sources")
            if not isinstance(sources,list):
                errors.append("EVIDENCE_SOURCES_INVALID:"+bid); sources=[]
            for source in sources:
                if not isinstance(source,Mapping):
                    errors.append("EVIDENCE_SOURCE_INVALID:"+bid); continue
                path=source.get("path"); sha=source.get("blob_sha")
                if not isinstance(path,str) or not path or not isinstance(sha,str) or not sha:
                    errors.append("EVIDENCE_SOURCE_IDENTITY_INVALID:"+bid); continue
                inspected.append({"path":path,"blob_sha":sha})
                try:
                    sem=_strings(source.get("semantic_residuals",[]),"semantic_residuals")
                    proc=_strings(source.get("procedural_limitations",[]),"procedural_limitations")
                    non=_strings(source.get("non_credit_limitations",[]),"non_credit_limitations")
                    declared=_strings(source.get("declared_limitations",[]),"declared_limitations")
                except ValueError as exc:
                    errors.append("EVIDENCE_CLASSIFICATION_INVALID:"+bid+":"+str(exc)); continue
                if sorted(declared)!=sorted(sem+proc+non):
                    errors.append("UNCLASSIFIED_OR_DUPLICATE_LIMITATION:"+bid+":"+path)
                semantic.extend("EVIDENCE::"+x for x in sem)
        elif row.get("proof_state")!="TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            errors.append("EVIDENCE_INDEX_MISSING:"+bid)
        if row.get("proof_state")=="TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            if blockers: errors.append("READY_ROUTE_HAS_BLOCKERS:"+bid)
            state="TERMINAL_READY"
        elif not inspection_complete:
            state="FAIL_CLOSED_UNINSPECTED"; semantic.append("COMPILER::EVIDENCE_INSPECTION_INCOMPLETE")
        elif semantic:
            state="SEMANTIC_RESIDUAL"
        elif mechanical:
            state="MECHANICAL_CLOSURE_READY"
        else:
            state="FAIL_CLOSED_NO_EXPLICIT_RESIDUAL"; semantic.append("COMPILER::NO_BLOCKER_AND_NOT_TERMINAL_READY")
        semantic=sorted(set(semantic))
        for item in semantic: semantic_dupes[item].append(bid)
        compiled.append({"behavior_id":bid,"compile_state":state,"proof_state":row.get("proof_state"),"semantic_residuals":semantic,"mechanical_gates":mechanical,"inspected_sources":inspected})
    compiled.sort(key=lambda x:x["behavior_id"])
    ready=[x["behavior_id"] for x in compiled if x["compile_state"]=="TERMINAL_READY"]
    auto=[x["behavior_id"] for x in compiled if x["compile_state"]=="MECHANICAL_CLOSURE_READY"]
    frontier=sorted(({"behavior_id":x["behavior_id"],"semantic_residual_count":len(x["semantic_residuals"]),"mechanical_gate_count":len(x["mechanical_gates"])} for x in compiled if x["compile_state"]=="SEMANTIC_RESIDUAL"),key=lambda x:(x["semantic_residual_count"],x["mechanical_gate_count"],x["behavior_id"]))
    dup=[{"residual":k,"behavior_ids":sorted(v)} for k,v in semantic_dupes.items() if len(v)>1]
    dup.sort(key=lambda x:x["residual"])
    return {"schema":SCHEMA,"status":"FAIL_CLOSED" if errors else "COMPILED_FAIL_CLOSED_FRONTIER","active_contract_count":len(compiled),"terminal_ready_count":len(ready),"terminal_ready":ready,"mechanical_closure_candidate_count":len(auto),"mechanical_closure_candidates":auto,"semantic_frontier":frontier,"mechanical_gate_histogram":dict(sorted(mech_hist.items())),"exact_duplicate_semantic_residuals":dup,"contracts":compiled,"errors":sorted(set(errors)),"execution_authority":False,"terminal_results_observed":0,"capability_credit_delta":0,"family_credit_delta":0,"rule":"BLOCKER_LIST_IS_A_PROJECTION__INSPECTED_EVIDENCE_MAY_ONLY_ADD_RESIDUALS__AUTO_CLOSURE_REQUIRES_ZERO_SEMANTIC_RESIDUALS_AND_COMPLETE_INSPECTION"}

def _clone(x): return json.loads(json.dumps(x))
def self_test():
    basis={"schema":BASIS_SCHEMA,"active_contract_count":3,"contracts":[{"behavior_id":"READY","proof_state":"TERMINAL_ROUTE_FROZEN_ADMISSIBLE","blockers":[]},{"behavior_id":"MECH","proof_state":"PENDING","blockers":["SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS","POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"]},{"behavior_id":"HIDDEN","proof_state":"PENDING","blockers":["SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS","POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"]}]}
    idx={"schema":INDEX_SCHEMA,"contracts":{"READY":{"inspection_complete":True,"sources":[]},"MECH":{"inspection_complete":True,"sources":[]},"HIDDEN":{"inspection_complete":True,"sources":[{"path":"r.json","blob_sha":"abc","declared_limitations":["BOUNDED_SCOPE"],"semantic_residuals":["BOUNDED_SCOPE"],"procedural_limitations":[],"non_credit_limitations":[]}]}}}
    out=compile_frontier(basis,idx); by={x["behavior_id"]:x for x in out["contracts"]}
    assert out["errors"]==[] and by["READY"]["compile_state"]=="TERMINAL_READY" and by["MECH"]["compile_state"]=="MECHANICAL_CLOSURE_READY" and by["HIDDEN"]["compile_state"]=="SEMANTIC_RESIDUAL"
    bad=_clone(idx); bad["contracts"]["HIDDEN"]["sources"][0]["semantic_residuals"]=[]
    assert compile_frontier(basis,bad)["status"]=="FAIL_CLOSED"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--basis",type=Path); ap.add_argument("--index",type=Path); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test:
        self_test(); print(json.dumps({"status":"SELF_TEST_PASS"},sort_keys=True)); return 0
    if a.basis is None or a.index is None: ap.error("--basis and --index required unless --self-test")
    out=compile_frontier(json.loads(a.basis.read_text()),json.loads(a.index.read_text())); print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not out["errors"] else 1
if __name__=="__main__": raise SystemExit(main())
