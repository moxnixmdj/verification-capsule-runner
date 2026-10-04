#!/usr/bin/env python3
import argparse, json, math, re, sys, time, urllib.request
from pathlib import Path

SCHEMA="PROJECT_BRAIN_ROOT1_SEMANTIC_SEED_GATE_V1"
RELATIONS=["BEFORE","AFTER","CAUSES","CONDITIONAL","CONTRAST","NONE"]

CASES=[
{
"id":"P1","task":"paraphrase",
"source":"After the pressure test succeeded, engineer Lina Noor sent eighteen cobalt cells to Oslo rather than Bergen in 2031.",
"expected":{"subject":"Lina Noor","item":"cobalt cells","quantity":"18","place":"Oslo","negated":"Bergen","relation":"BEFORE"},
"anchors":[["lina"],["18","eighteen"],["cobalt"],["oslo"],["bergen"],["2031"]],
"words":[14,42]
},
{
"id":"P2","task":"paraphrase",
"source":"The committee rejected the blue prototype, but it approved the silver prototype only after that device ran for fourteen hours without overheating.",
"expected":{"subject":"committee","item":"silver prototype","quantity":"14","place":"none","negated":"blue prototype","relation":"CONDITIONAL"},
"anchors":[["committee"],["silver"],["blue"],["14","fourteen"],["hour"]],
"words":[16,48]
},
{
"id":"S1","task":"simplify",
"source":"Because the northern pump was offline, the clinic moved twenty-seven vaccine boxes to Warehouse C before dawn; despite the delay, none were sent to Warehouse D.",
"expected":{"subject":"clinic","item":"vaccine boxes","quantity":"27","place":"Warehouse C","negated":"Warehouse D","relation":"CAUSES"},
"anchors":[["clinic"],["vaccine"],["27","twenty-seven","twenty seven"],["warehouse c"],["warehouse d"],["pump"]],
"words":[18,55]
},
{
"id":"S2","task":"simplify",
"source":"Although Mara had reserved the west hall, the safety officer moved the forty-two guests to the east hall after smoke was detected, and nobody returned west that evening.",
"expected":{"subject":"safety officer","item":"guests","quantity":"42","place":"east hall","negated":"west hall","relation":"AFTER"},
"anchors":[["safety"],["guest"],["42","forty-two","forty two"],["east hall"],["west hall"],["smoke"]],
"words":[18,58]
},
{
"id":"M1","task":"summarize",
"source":"At 07:10, the research ship Ardent reached Port Selene with 36 sealed water samples. The team had planned to unload at Port Mira, but ice closed that harbor. A drone inspection found no damaged seals. The samples were transferred to the Selene laboratory by noon.",
"expected":{"subject":"Ardent","item":"water samples","quantity":"36","place":"Port Selene","negated":"Port Mira","relation":"CAUSES"},
"anchors":[["ardent"],["water sample"],["36","thirty-six","thirty six"],["selene"],["mira"],["ice"]],
"words":[22,55]
},
{
"id":"M2","task":"summarize",
"source":"The town council voted 8 to 3 to open the Cedar footbridge on Monday. An earlier engineering note had recommended Tuesday, but a final load test passed on Sunday afternoon. The road bridge stayed closed. No injuries were reported during the inspection.",
"expected":{"subject":"town council","item":"Cedar footbridge","quantity":"8 to 3","place":"none","negated":"road bridge","relation":"BEFORE"},
"anchors":[["council"],["cedar"],["8"],["3"],["monday"],["road bridge"],["load test"]],
"words":[20,55]
},
{
"id":"T1","task":"story_generation",
"source":"Write a short coherent story from these facts: Asha finds a brass key in the library. The storm ends. Asha enters the greenhouse with the key. She mails a leaf sample to Dr. Iven. She does not mail the key.",
"expected":{"subject":"Asha","item":"brass key","quantity":"1","place":"greenhouse","negated":"mail the key","relation":"BEFORE","event_order":["key","storm","greenhouse","sample"]},
"anchors":[["asha"],["key"],["storm"],["greenhouse"],["sample"],["iven"]],
"words":[55,135]
},
{
"id":"T2","task":"story_generation",
"source":"Write a short coherent story from these facts: Niko repairs the radio before sunrise. At sunrise a ferry arrives carrying 12 crates. Niko takes the crates to Dock Seven. He leaves the radio in the workshop and does not take it to the dock.",
"expected":{"subject":"Niko","item":"crates","quantity":"12","place":"Dock Seven","negated":"radio to the dock","relation":"BEFORE","event_order":["radio","sunrise","ferry","dock"]},
"anchors":[["niko"],["radio"],["sunrise"],["ferry"],["12","twelve"],["dock seven"]],
"words":[55,135]
}
]

NUMBER_WORDS={
"zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
"eleven":"11","twelve":"12","thirteen":"13","fourteen":"14","fifteen":"15","sixteen":"16","seventeen":"17","eighteen":"18",
"nineteen":"19","twenty":"20","twenty-seven":"27","twenty seven":"27","thirty-six":"36","thirty six":"36","forty-two":"42","forty two":"42"
}

def norm(v):
    s=str(v if v is not None else "").lower().strip()
    s=s.replace("–","-").replace("—","-")
    for k,val in sorted(NUMBER_WORDS.items(), key=lambda kv:-len(kv[0])):
        s=re.sub(r"\b"+re.escape(k)+r"\b",val,s)
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def extract_json(text):
    text=str(text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        a=text.find("{"); b=text.rfind("}")
        if a<0 or b<a: raise ValueError("NO_JSON_OBJECT")
        return json.loads(text[a:b+1])

def has_anchor(text, alternatives):
    n=norm(text)
    return any(norm(x) in n for x in alternatives)

def copied_span(source, out, n=8):
    a=norm(source).split(); b=" "+norm(out)+" "
    if len(a)<n: return False
    return any(" "+" ".join(a[i:i+n])+" " in b for i in range(len(a)-n+1))

def fact_score(actual, expected):
    if not isinstance(actual,dict): return 0.0,{}
    details={}
    scores=[]
    for k,v in expected.items():
        av=actual.get(k)
        if k=="event_order":
            good=False
            if isinstance(av,list) and len(av)==len(v):
                good=all(norm(want) in norm(got) for got,want in zip(av,v))
            score=1.0 if good else 0.0
        elif k=="relation":
            score=1.0 if str(av or "").strip().upper()==str(v).upper() else 0.0
        elif k=="quantity":
            score=1.0 if norm(av)==norm(v) else 0.0
        else:
            score=1.0 if norm(av)==norm(v) else 0.0
        details[k]=score; scores.append(score)
    return sum(scores)/len(scores),details

def text_score(case,text):
    if not isinstance(text,str) or not text.strip(): return 0.0,{"empty":True}
    wc=len(re.findall(r"\b\w+[\w'-]*\b",text))
    lo,hi=case["words"]
    length_ok=lo<=wc<=hi
    anchor_scores=[1.0 if has_anchor(text,a) else 0.0 for a in case["anchors"]]
    anchor=sum(anchor_scores)/len(anchor_scores)
    copy_ok=not copied_span(case["source"],text,8) if case["task"]!="story_generation" else True
    simplicity=1.0
    if case["task"]=="simplify":
        sents=[x for x in re.split(r"[.!?]+",text) if x.strip()]
        avg=wc/max(1,len(sents))
        simplicity=1.0 if avg<=16 else max(0.0,16.0/avg)
    score=0.55*anchor+0.20*(1.0 if length_ok else 0.0)+0.15*(1.0 if copy_ok else 0.0)+0.10*simplicity
    return score,{"word_count":wc,"length_ok":length_ok,"anchor_fraction":anchor,"copy8_ok":copy_ok,"simplicity":simplicity}

def prompt_for(case):
    return f"""You are taking a semantic transformation test. Preserve meaning exactly.
TASK: {case['task']}
SOURCE:
{case['source']}

Return ONLY one JSON object with this shape:
{{
  "transformed_text": "...",
  "facts": {{
    "subject": "...",
    "item": "...",
    "quantity": "...",
    "place": "...",
    "negated": "...",
    "relation": "..."
  }}
}}
For story_generation also add facts.event_order as an array of four short event labels in chronological order.
Rules:
- facts must describe what the SOURCE means, not what words happen to be nearby.
- Use "none" only when a requested slot truly has no place.
- relation must be one of {RELATIONS}.
- Preserve negation, quantities, causal/temporal direction, entities, and event order.
- transformed_text must perform the requested task naturally and must not merely copy the source.
- Do not add facts not supported by the source.
"""

def call(endpoint,case,max_tokens=260):
    body={
      "model":"local",
      "messages":[
        {"role":"system","content":"Return strict JSON only. Do not reveal reasoning."},
        {"role":"user","content":prompt_for(case)}
      ],
      "temperature":0,
      "max_tokens":max_tokens,
      "chat_template_kwargs":{"enable_thinking":False}
    }
    req=urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=240) as r:
        obj=json.loads(r.read().decode())
    content=obj["choices"][0]["message"].get("content") or ""
    return content,round(time.monotonic()-t,3)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--endpoint",default="http://127.0.0.1:8080/v1/chat/completions")
    ap.add_argument("--out",default="root1_semantic_seed_result.json")
    args=ap.parse_args()
    rows=[]
    for case in CASES:
        row={"id":case["id"],"task":case["task"]}
        try:
            raw,lat=call(args.endpoint,case)
            parsed=extract_json(raw)
            fs,fd=fact_score(parsed.get("facts"),case["expected"])
            ts,td=text_score(case,parsed.get("transformed_text"))
            score=0.72*fs+0.28*ts
            row.update({"status":"SCORED","latency_s":lat,"fact_score":fs,"text_score":ts,"score":score,
                        "fact_details":fd,"text_details":td,"parsed":parsed,"raw":raw})
        except Exception as e:
            row.update({"status":"ERROR","error":type(e).__name__+":"+str(e),"fact_score":0.0,"text_score":0.0,"score":0.0})
        rows.append(row)
        print(json.dumps({k:row[k] for k in row if k not in {"parsed","raw"}},sort_keys=True),flush=True)
    mean=sum(r["score"] for r in rows)/len(rows)
    fact_mean=sum(r["fact_score"] for r in rows)/len(rows)
    task_means={}
    for task in sorted({r["task"] for r in rows}):
        vals=[r["score"] for r in rows if r["task"]==task]
        task_means[task]=sum(vals)/len(vals)
    # Minimum semantic-seed gate: no case may collapse, facts must be nearly exact,
    # and every transformation family must clear a floor. This is deliberately
    # narrower than any Opus-equivalence claim.
    passed=(fact_mean>=0.95 and mean>=0.88 and min(r["score"] for r in rows)>=0.70
            and min(task_means.values())>=0.82 and all(r["status"]=="SCORED" for r in rows))
    result={
      "schema":SCHEMA,
      "status":"PASS_MINIMUM_SEMANTIC_SEED" if passed else "FAIL_MINIMUM_SEMANTIC_SEED",
      "case_count":len(rows),
      "mean_score":mean,
      "fact_mean":fact_mean,
      "task_means":task_means,
      "thresholds":{"fact_mean_gte":0.95,"mean_gte":0.88,"case_min_gte":0.70,"task_mean_min_gte":0.82},
      "terminal_case_content_used":False,
      "terminal_credit":0,
      "opus_equivalence_credit":0,
      "rows":rows
    }
    Path(args.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},sort_keys=True))
    return 0 if passed else 2

if __name__=="__main__":
    raise SystemExit(main())
