#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys, urllib.request

SERVER="http://127.0.0.1:8080/v1/chat/completions"
CASES=[
{"id":"PARA_1","effect":"text.paraphrase.semantic_preserving","instruction":"Paraphrase the sentence without changing any facts. Use one sentence and no more than 24 words. Return only the answer.","source":"Neris delivered seven amber parcels to Corin before sunrise on Tuesday.","required":[["neris"],["corin"],["seven","7"],["amber"],["tuesday"]],"max_words":24,"max_sentences":1,"forbid_exact":True,"min_change":True},
{"id":"PARA_2","effect":"text.paraphrase.semantic_preserving","instruction":"Paraphrase the sentence without changing any facts. Use one sentence and no more than 28 words. Return only the answer.","source":"The observatory postponed the Lumen-4 launch by three days because high winds crossed the ridge.","required":[["lumen-4","lumen 4"],["three","3"],["wind"],["ridge"],["postpon","delay"]],"max_words":28,"max_sentences":1,"forbid_exact":True,"min_change":True},
{"id":"SIMPLE_1","effect":"text.simplify.semantic_preserving","instruction":"Rewrite this in simple everyday English in no more than 14 words. Preserve who did what and where. Return only the answer.","source":"Following the cessation of precipitation, Mira initiated pedestrian transit toward the eastern laboratory.","required":[["mira"],["east","eastern"],["lab","laboratory"],["walk","went","go","headed","moved","travel"]],"max_words":14,"min_change":True},
{"id":"SIMPLE_2","effect":"text.simplify.semantic_preserving","instruction":"Rewrite this in simple everyday English in no more than 18 words. Preserve the cause and action. Return only the answer.","source":"Because the photovoltaic array ceased generating energy after dusk, Tovan activated the reserve battery.","required":[["tovan"],["battery"],["solar","photovoltaic"],["dusk","night","dark"],["because","so","when","after"]],"max_words":18,"min_change":True},
{"id":"SUM_1","effect":"text.summarize.faithful","instruction":"Summarize the report in one sentence of no more than 22 words. Keep the mission result and return event. Return only the answer.","source":"The Alba rover traveled twelve kilometers across the plain. Its battery fell to 41 percent. At Site K it collected a basalt sample. Alba returned to base at 18:20 without damage.","required":[["alba"],["basalt"],["site k","site-k"],["return","base"],["without damage","undamaged","safe"]],"max_words":22,"max_sentences":1},
{"id":"SUM_2","effect":"text.summarize.faithful","instruction":"Summarize the report in one sentence of no more than 22 words. Keep the decision, reason, and new time. Return only the answer.","source":"The Delta team inspected Bridge 6 at 09:00. Engineers found ice on the north joints. The team postponed the load test for safety. The replacement test is scheduled for Friday at 14:00.","required":[["delta"],["bridge 6","bridge-6"],["ice"],["postpon","delay"],["friday"],["14:00","2:00","2 pm","2pm"]],"max_words":22,"max_sentences":1},
{"id":"STORY_1","effect":"text.story.generate_instruction_grounded","instruction":"Write exactly three short sentences. In order: Nara finds a brass key; she opens a green box with it; she gives the map inside to Ivo. Return only the story.","source":"","required":[["nara"],["brass"],["key"],["green"],["box"],["map"],["ivo"]],"ordered":[["nara","key"],["green","box"],["map","ivo"]],"max_words":45,"exact_sentences":3},
{"id":"STORY_2","effect":"text.story.generate_instruction_grounded","instruction":"Write exactly three short sentences. In order: Aris lights a lantern; he crosses the old bridge; he uses the lantern to guide a lost dog home. Return only the story.","source":"","required":[["aris"],["lantern"],["bridge"],["dog"],["home"]],"ordered":[["aris","lantern"],["bridge"],["dog","home"]],"max_words":45,"exact_sentences":3},
]

def norm(s:str)->str:
    return " ".join(s.lower().split())

def strip_reasoning(s:str)->str:
    s=re.sub(r"<think>.*?</think>","",s,flags=re.I|re.S)
    return s.strip()

def words(s:str)->list[str]:
    return re.findall(r"\b[\w'-]+\b",s,flags=re.UNICODE)

def sentences(s:str)->list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+",s.strip()) if x.strip()]

def contains_any(text:str, group:list[str])->bool:
    t=norm(text)
    return any(norm(x) in t for x in group)

def ordered_ok(text:str, groups:list[list[str]])->bool:
    t=norm(text); pos=-1
    for group in groups:
        hits=[t.find(norm(x),pos+1) for x in group]
        hits=[x for x in hits if x>=0]
        if not hits: return False
        pos=min(hits)
    return True

def call(prompt:str,seed:int)->str:
    body={
      "model":"local",
      "messages":[{"role":"user","content":prompt}],
      "temperature":0.6,"top_p":0.95,"max_tokens":192,"seed":seed,
      "stream":False
    }
    req=urllib.request.Request(SERVER,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=300) as r:
        d=json.load(r)
    return strip_reasoning(str(d["choices"][0]["message"]["content"]))

def grade(case:dict,out:str)->dict:
    checks={}
    checks["required_groups"]=all(contains_any(out,g) for g in case.get("required",[]))
    checks["max_words"]=len(words(out))<=case["max_words"]
    if "max_sentences" in case: checks["max_sentences"]=len(sentences(out))<=case["max_sentences"]
    if "exact_sentences" in case: checks["exact_sentences"]=len(sentences(out))==case["exact_sentences"]
    if case.get("forbid_exact"): checks["forbidden_exact"]=norm(out)!=norm(case["source"])
    if case.get("min_change"): checks["min_source_change"]=norm(out)!=norm(case["source"])
    if case.get("ordered"): checks["ordered_groups"]=ordered_ok(out,case["ordered"])
    return {"checks":checks,"pass":all(checks.values()),"word_count":len(words(out)),"sentence_count":len(sentences(out))}

def main()->int:
    results=[]
    for i,c in enumerate(CASES):
        prompt=c["instruction"] + (("\n\nSOURCE:\n"+c["source"]) if c["source"] else "")
        out=call(prompt,424200+i)
        g=grade(c,out)
        results.append({"id":c["id"],"effect":c["effect"],"output":out,**g})
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    by_effect={}
    for r in results: by_effect.setdefault(r["effect"],[]).append(r["pass"])
    effect_pass={k:all(v) for k,v in by_effect.items()}
    receipt={
      "schema":"PROJECT_BRAIN_QWEN38_4B_SEMANTIC_SEED_EXECUTION_RECEIPT_V1",
      "subject":{"repository":"empero-ai/Qwen3.8-4B-Distill-GGUF","revision":"391fc7d103e3942a408def3e4f51c2f85d464417","file":"Qwen3.8-4B-Q4_K_M.gguf","bytes":2783446304,"sha256":"dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790"},
      "runtime":{"llama_cpp_commit":"0504396140d1c882f5f6ee34466a42db7ae90114","threads":4,"context_tokens":4096,"temperature":0.6,"top_p":0.95,"attempts_per_case":1},
      "results":results,"effect_pass":effect_pass,"suite_pass":all(r["pass"] for r in results),
      "accounting":{"incremental_spend_usd":0,"terminal_cases_consumed":0,"adaptive_retries":0},
      "hard_nonclaims":["BOUNDED_NONTERMINAL_SEED_TEST_ONLY","NO_OPUS55_SEMANTIC_EQUIVALENCE_CLAIM","NO_LIVEBENCH_SCORE_INHERITANCE","NO_TERMINAL_ACCEPTANCE_OR_OWNERSHIP_CREDIT"]
    }
    open("qwen38_4b_semantic_seed_receipt_v1.json","w",encoding="utf-8").write(json.dumps(receipt,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    return 0 if receipt["suite_pass"] else 3

if __name__=="__main__":
    raise SystemExit(main())
