#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parents[2]
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"guarded-pr450-claim-spec-qualification-report.json"

def load_candidate():
    p=CAP/"objective_claim_operand_binding.py"
    s=importlib.util.spec_from_file_location("guarded_pr450_candidate",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def sha(v):
    if isinstance(v,str): v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()

def extraction(texts,url):
    visible_text="\n".join(texts)
    page=sha("fresh-page|"+url+"|"+visible_text)
    visible=sha(visible_text)
    rows=[]; cursor=0
    for text in texts:
        tsha=sha(text); start=cursor; end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        rows.append({"evidence_unit_id":uid,"source_url":url,"page_raw_sha256":page,
          "visible_text_sha256":visible,"text":text,"text_sha256":tsha,
          "visible_text_start":start,"visible_text_end":end})
        cursor=end+1
    return {"schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","output_verified":True,
      "source_url":url,"page_raw_sha256":page,"visible_text_sha256":visible,"evidence_units":rows}

def eq(a,b,label):
    if a!=b: raise AssertionError(f"{label}: expected {b!r}, got {a!r}")

def pred(a,b,op,t=None):
    a=Decimal(a); b=Decimal(b)
    return {"GT":a>b,"LT":a<b,"GTE":a>=b,"LTE":a<=b,"EQ":a==b,"NE":a!=b,
      "ABS_DIFF_LTE":abs(a-b)<=Decimal(t) if t is not None else False}[op]

def positive(cand,c):
    data=extraction([c["left_text"],c["right_text"]],c["url"])
    out=cand.bind(c["objective"],data,evaluate_relation=True)
    eq(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",c["id"]+" status")
    eq(out["relation_spec"]["operator"],c["op"],c["id"]+" operator")
    eq(out["relation_result"]["predicate"],pred(c["left"],c["right"],c["op"],c.get("threshold")),c["id"]+" predicate")
    eq(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",c["id"]+" relation")
    eq(out["model_dependency_count"],0,c["id"]+" model_dependency")
    if c["left_anchor"].lower() not in out["left_binding"]["text"].lower(): raise AssertionError(c["id"]+" left role")
    if c["right_anchor"].lower() not in out["right_binding"]["text"].lower(): raise AssertionError(c["id"]+" right role")
    return {"id":c["id"],"status":"PASS","operator":c["op"],"predicate":out["relation_result"]["predicate"]}

def main():
    cand=load_candidate()
    cases=[
      {"id":"GEOSCIENCE_GT_TRUE","objective":"Basalt Sample R density is higher than Granite Sample S density.",
       "left_text":"Basalt Sample R density was 3.12 g/cm3.","right_text":"Granite Sample S density was 2.75 g/cm3.",
       "left_anchor":"Basalt Sample R","right_anchor":"Granite Sample S","left":"3.12","right":"2.75","op":"GT","url":"https://fresh.example/geoscience"},
      {"id":"HYDROLOGY_LT_TRUE","objective":"Determine whether Basin East nitrate concentration is lower than Basin West nitrate concentration.",
       "left_text":"Basin East nitrate concentration was 4.8 mg/L.","right_text":"Basin West nitrate concentration was 6.1 mg/L.",
       "left_anchor":"Basin East","right_anchor":"Basin West","left":"4.8","right":"6.1","op":"LT","url":"https://fresh.example/hydrology"},
      {"id":"THERMAL_GTE_EQUAL","objective":"Shield Alpha temperature is at least Shield Beta temperature.",
       "left_text":"Shield Alpha temperature was 640 K.","right_text":"Shield Beta temperature was 640 K.",
       "left_anchor":"Shield Alpha","right_anchor":"Shield Beta","left":"640","right":"640","op":"GTE","url":"https://fresh.example/thermal"},
      {"id":"OPTICS_LTE_TRUE","objective":"Fiber North attenuation is at most Fiber South attenuation.",
       "left_text":"Fiber North attenuation was 0.19 dB.","right_text":"Fiber South attenuation was 0.23 dB.",
       "left_anchor":"Fiber North","right_anchor":"Fiber South","left":"0.19","right":"0.23","op":"LTE","url":"https://fresh.example/optics"},
      {"id":"MECHANICAL_EQ_TRUE","objective":"Rotor A speed is equal to Rotor B speed.",
       "left_text":"Rotor A speed was 3600 rpm.","right_text":"Rotor B speed was 3600 rpm.",
       "left_anchor":"Rotor A","right_anchor":"Rotor B","left":"3600","right":"3600","op":"EQ","url":"https://fresh.example/mechanical"},
      {"id":"MATERIALS_NE_TRUE","objective":"Composite X modulus is different from Composite Y modulus.",
       "left_text":"Composite X modulus was 72 GPa.","right_text":"Composite Y modulus was 68 GPa.",
       "left_anchor":"Composite X","right_anchor":"Composite Y","left":"72","right":"68","op":"NE","url":"https://fresh.example/materials"},
      {"id":"RADIO_ABS_DIFF_TRUE","objective":"Beacon A frequency and Beacon B frequency differ by at most 0.4 MHz.",
       "left_text":"Beacon A frequency was 1420.1 MHz.","right_text":"Beacon B frequency was 1420.4 MHz.",
       "left_anchor":"Beacon A","right_anchor":"Beacon B","left":"1420.1","right":"1420.4","op":"ABS_DIFF_LTE","threshold":"0.4","url":"https://fresh.example/radio"},
      {"id":"PRESSURE_GT_FALSE","objective":"Tank Red pressure exceeds Tank Blue pressure.",
       "left_text":"Tank Red pressure was 5.0 bar.","right_text":"Tank Blue pressure was 5.5 bar.",
       "left_anchor":"Tank Red","right_anchor":"Tank Blue","left":"5.0","right":"5.5","op":"GT","url":"https://fresh.example/pressure"},
    ]
    report={"schema":"PROJECT_BRAIN_GUARDED_PR450_FRESH_QUALIFICATION_V1",
      "fresh_case_set":"NEVER_EXECUTED_BEFORE_THIS_GUARDED_PROBLEM_IDENTITY",
      "positive":[],"negative":[],"model_dependency_count":0,"incremental_spend_usd":0}
    for c in cases: report["positive"].append(positive(cand,c))

    q="The watchdog interval is 17 milliseconds."
    out=cand.bind('Verify whether the evidence states "The watchdog interval is 17 milliseconds."',extraction([q,"Build identifier was 404."],"https://fresh.example/software"),True)
    eq(out["status"],"CLAIM_SPEC_BOUND","quoted status"); eq(out["relation_result"]["status"],"EXACT_TEXT_SUPPORT_VERIFIED","quoted result")
    report["positive"].append({"id":"FRESH_EXACT_QUOTED_SUPPORT","status":"PASS"})

    neg=extraction(["Basin East nitrate concentration was 4.8 mg/L.","Basin West nitrate concentration was 6.1 mg/L."],"https://fresh.example/neg")
    out=cand.bind("Compare Basin East and Basin West nitrate concentration.",neg,False)
    eq(out["reason"],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED","unsupported"); report["negative"].append({"id":"UNSUPPORTED","status":"PASS"})

    amb=extraction(["Basin East nitrate concentration was 4.8 mg/L.","Basin East nitrate concentration was 4.9 mg/L.","Basin West nitrate concentration was 6.1 mg/L."],"https://fresh.example/amb")
    out=cand.bind("Determine whether Basin East nitrate concentration is lower than Basin West nitrate concentration.",amb,False)
    eq(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY","referent ambiguity"); report["negative"].append({"id":"REFERENT_AMBIGUITY","status":"PASS"})

    units=extraction(["Tank Red pressure was 5.0 bar.","Tank Blue pressure was 500 kPa."],"https://fresh.example/units")
    out=cand.bind("Tank Red pressure exceeds Tank Blue pressure.",units,False)
    eq(out["reason"],"NO_EXACT_UNIT_COMPATIBLE_OPERAND_PAIR","unit mismatch"); report["negative"].append({"id":"UNIT_MISMATCH","status":"PASS"})

    multi=extraction(["Fiber North attenuation was 0.19 dB and revised to 0.20 dB.","Fiber South attenuation was 0.23 dB."],"https://fresh.example/multi")
    out=cand.bind("Fiber North attenuation is lower than Fiber South attenuation.",multi,False)
    eq(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR","multiple values"); report["negative"].append({"id":"MULTIPLE_VALUES","status":"PASS"})

    decoy=extraction(["Basin East nitrate concentration in 2026 was 4.8 mg/L.","Basin West nitrate concentration in 2025 was 6.1 mg/L."],"https://fresh.example/decoy")
    out=cand.bind("Basin East nitrate concentration is lower than Basin West nitrate concentration.",decoy,True)
    eq(out["operand_pair"]["left_surface"],"4.8 mg/L","year decoy left"); eq(out["operand_pair"]["right_surface"],"6.1 mg/L","year decoy right")
    report["negative"].append({"id":"YEAR_DECOY_REJECTED","status":"PASS"})

    try:
        cand.bind("Beacon A frequency and Beacon B frequency differ by at most 0.4 kHz.",
          extraction(["Beacon A frequency was 1420.1 MHz.","Beacon B frequency was 1420.4 MHz."],"https://fresh.example/threshold"),True)
    except ValueError as e:
        if "THRESHOLD_UNIT_MISMATCH" not in str(e): raise
    else: raise AssertionError("threshold mismatch accepted")
    report["negative"].append({"id":"THRESHOLD_UNIT_MISMATCH","status":"PASS"})

    dup=extraction([q,q],"https://fresh.example/dup")
    out=cand.bind('Verify the exact claim "watchdog interval is 17 milliseconds."',dup,False)
    eq(out["reason"],"EXACT_QUOTED_CLAIM_EVIDENCE_AMBIGUOUS","duplicate quote"); report["negative"].append({"id":"DUPLICATE_QUOTE","status":"PASS"})

    tam=extraction(["Composite X modulus was 72 GPa.","Composite Y modulus was 68 GPa."],"https://fresh.example/tamper")
    tam["evidence_units"][0]["text"]+=" altered"
    try: cand.bind("Composite X modulus is different from Composite Y modulus.",tam,True)
    except ValueError: pass
    else: raise AssertionError("tampered evidence accepted")
    report["negative"].append({"id":"TAMPERED_EVIDENCE","status":"PASS"})

    report["status"]="PASS"
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__": main()
