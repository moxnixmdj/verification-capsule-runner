#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,json,pathlib
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"guarded-claim-spec-fresh-qualification-b-report.json"

def sha(v):
    if isinstance(v,str): v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()

def load():
    p=CAP/"objective_claim_operand_binding.py"
    s=importlib.util.spec_from_file_location("fresh_b_candidate",p)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def extraction(texts,url):
    page=sha("page-b|"+"|".join(texts));visible="\n".join(texts);vh=sha(visible)
    rows=[];cursor=0
    for text in texts:
        th=sha(text);start=cursor;end=start+len(text);uid=sha(f"{page}:{start}:{end}:{th}")
        rows.append({"evidence_unit_id":uid,"source_url":url,"page_raw_sha256":page,"visible_text_sha256":vh,"text":text,"text_sha256":th,"visible_text_start":start,"visible_text_end":end})
        cursor=end+1
    return {"schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2","status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","output_verified":True,"source_url":url,"page_raw_sha256":page,"visible_text_sha256":vh,"evidence_units":rows}

def eq(a,b,label):
    if a!=b: raise AssertionError(f"{label}: expected {b!r}, got {a!r}")

def relation_case(m,c):
    data=extraction([c["left_text"],c["right_text"]],c["url"])
    out=m.bind(c["objective"],data,evaluate_relation=True)
    eq(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",c["id"]+" status")
    eq(out["relation_spec"]["operator"],c["operator"],c["id"]+" operator")
    eq(out["relation_result"]["predicate"],c["predicate"],c["id"]+" predicate")
    eq(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",c["id"]+" verified")
    eq(out["model_dependency_count"],0,c["id"]+" model")
    return {"id":c["id"],"status":"PASS","operator":c["operator"],"predicate":out["relation_result"]["predicate"]}

def must_reason(m,objective,texts,reason,label):
    out=m.bind(objective,extraction(texts,"https://fresh-b.example/"+label),evaluate_relation=False)
    eq(out.get("reason"),reason,label)
    return {"id":label,"status":"PASS"}

def main():
    m=load()
    cases=[
      {"id":"HYDRAULICS_GT","objective":"Does Reservoir Cedar pressure exceed Reservoir Birch pressure?","left_text":"In 2024 Reservoir Cedar pressure was 16.4 bar.","right_text":"In 2025 Reservoir Birch pressure was 12.1 bar.","operator":"GT","predicate":True,"url":"https://fresh-b.example/hydraulics"},
      {"id":"ORBITAL_LT_LABELS","objective":"Satellite Orion A jitter is lower than Satellite Orion B jitter.","left_text":"Satellite Orion A jitter was 3.2 ms.","right_text":"Satellite Orion B jitter was 4.5 ms.","operator":"LT","predicate":True,"url":"https://fresh-b.example/orbit"},
      {"id":"ENERGY_GTE_EQUAL","objective":"Battery North capacity is at least Battery South capacity.","left_text":"Battery North capacity was 82 Wh.","right_text":"Battery South capacity was 82 Wh.","operator":"GTE","predicate":True,"url":"https://fresh-b.example/energy"},
      {"id":"PIPELINE_LTE","objective":"Pipeline East leak rate is at most Pipeline West leak rate.","left_text":"Pipeline East leak rate was 1.4 L/s.","right_text":"Pipeline West leak rate was 1.6 L/s.","operator":"LTE","predicate":True,"url":"https://fresh-b.example/pipeline"},
      {"id":"MODULE_EQ","objective":"Module Red checksum count is equal to Module Blue checksum count.","left_text":"Module Red checksum count was 512 count.","right_text":"Module Blue checksum count was 512 count.","operator":"EQ","predicate":True,"url":"https://fresh-b.example/module"},
      {"id":"QUEUE_NE","objective":"Node Primary queue depth is different from Node Secondary queue depth.","left_text":"Node Primary queue depth was 18 items.","right_text":"Node Secondary queue depth was 22 items.","operator":"NE","predicate":True,"url":"https://fresh-b.example/queue"},
      {"id":"VOLTAGE_ABS_DIFF","objective":"Station Delta voltage and Station Gamma voltage differ by at most 0.3 V.","left_text":"Station Delta voltage was 4.9 V.","right_text":"Station Gamma voltage was 5.1 V.","operator":"ABS_DIFF_LTE","predicate":True,"url":"https://fresh-b.example/voltage"}
    ]
    positive=[relation_case(m,c) for c in cases]
    claim="The maintenance window starts at 02:00 UTC."
    q=m.bind('Verify whether the evidence states "The maintenance window starts at 02:00 UTC."',extraction([claim,"Reference revision is 17."],"https://fresh-b.example/quoted"),evaluate_relation=True)
    eq(q["status"],"CLAIM_SPEC_BOUND","quoted status");eq(q["relation_result"]["status"],"EXACT_TEXT_SUPPORT_VERIFIED","quoted result")
    positive.append({"id":"OPS_QUOTED_SUPPORT","status":"PASS"})
    negative=[]
    negative.append(must_reason(m,"Does Reservoir Cedar pressure exceed Reservoir Birch pressure?",["Reservoir Cedar pressure was 16.4 bar.","Reservoir Cedar pressure at backup sensor was 16.3 bar.","Reservoir Birch pressure was 12.1 bar."],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY","AMBIGUOUS_REFERENT"))
    negative.append(must_reason(m,"Does Reservoir Cedar pressure exceed Reservoir Birch pressure?",["Reservoir Cedar pressure was 16.4 bar and later 16.5 bar.","Reservoir Birch pressure was 12.1 bar."],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR","MULTIPLE_VALUES"))
    negative.append(must_reason(m,"Does Reservoir Cedar pressure exceed Reservoir Birch pressure?",["Reservoir Cedar pressure was 16.4 bar.","Reservoir Birch pressure was 1210 kPa."],"NO_EXACT_UNIT_COMPATIBLE_OPERAND_PAIR","UNIT_MISMATCH"))
    negative.append(must_reason(m,"Compare Reservoir Cedar and Reservoir Birch pressure.",["Reservoir Cedar pressure was 16.4 bar.","Reservoir Birch pressure was 12.1 bar."],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED","UNSUPPORTED_GRAMMAR"))
    dup=extraction([claim,claim],"https://fresh-b.example/duplicate")
    d=m.bind('Verify the exact claim "maintenance window starts at 02:00 UTC."',dup,evaluate_relation=False)
    eq(d["reason"],"EXACT_QUOTED_CLAIM_EVIDENCE_AMBIGUOUS","DUPLICATE_QUOTED")
    negative.append({"id":"DUPLICATE_QUOTED","status":"PASS"})
    tam=extraction(["Module Red checksum count was 512 count.","Module Blue checksum count was 512 count."],"https://fresh-b.example/tamper")
    tam["evidence_units"][0]["text"]+=" altered"
    try:
        m.bind("Module Red checksum count is equal to Module Blue checksum count.",tam,evaluate_relation=True)
    except ValueError as exc:
        if not any(x in str(exc) for x in ("TEXT_HASH_MISMATCH","OFFSET_INVALID")): raise
    else: raise AssertionError("TAMPERED_EVIDENCE_ACCEPTED")
    negative.append({"id":"TAMPERED_EVIDENCE","status":"PASS"})
    report={"schema":"PROJECT_BRAIN_GUARDED_CLAIM_SPEC_FRESH_QUALIFICATION_B_V1","status":"PASS","positive_checks":positive,"negative_checks":negative,"model_dependency_count":0,"incremental_spend_usd":0,"parent_task_execution":False,"parent_task_replay":False}
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__": main()
