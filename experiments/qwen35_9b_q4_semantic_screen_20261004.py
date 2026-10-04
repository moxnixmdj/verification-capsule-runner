#!/usr/bin/env python3
from __future__ import annotations
import json, re, urllib.request

URL="http://127.0.0.1:8080/v1/chat/completions"
MODEL="brain-qwen3.5-9b"
TASKS=[
 {"id":"para_1","kind":"paraphrase","source":"Mira paid 18 dollars for the blue notebook on Tuesday because she needed it for class.","prompt":"Paraphrase the following sentence without changing its meaning: Mira paid 18 dollars for the blue notebook on Tuesday because she needed it for class.","must":["mira","18","tuesday"]},
 {"id":"para_2","kind":"paraphrase","source":"Orion Labs postponed the satellite launch from May 4 to May 9 because strong winds made the original date unsafe.","prompt":"Rewrite this sentence using different wording while preserving every fact: Orion Labs postponed the satellite launch from May 4 to May 9 because strong winds made the original date unsafe.","must":["orion","may 4","may 9"]},
 {"id":"para_3","kind":"paraphrase","source":"Nadia sent the report to Karim before lunch so he could review it before the meeting.","prompt":"Paraphrase without adding or removing facts: Nadia sent the report to Karim before lunch so he could review it before the meeting.","must":["nadia","karim"]},
 {"id":"simple_1","kind":"simplify","source":"Although the rainfall continued intermittently throughout the morning, the school administrators determined that the outdoor event could proceed once the weather improved.","prompt":"Rewrite in simpler English while preserving the meaning: Although the rainfall continued intermittently throughout the morning, the school administrators determined that the outdoor event could proceed once the weather improved.","must":["school","event"]},
 {"id":"simple_2","kind":"simplify","source":"The committee elected to defer implementation of the revised policy until the legal department had completed its review.","prompt":"Make this sentence easier to understand without changing the facts: The committee elected to defer implementation of the revised policy until the legal department had completed its review.","must":["committee","legal"]},
 {"id":"simple_3","kind":"simplify","source":"Dr. Salma instructed Omar to consume the medication with food in order to reduce the likelihood of stomach irritation.","prompt":"Simplify this sentence but keep all important facts: Dr. Salma instructed Omar to consume the medication with food in order to reduce the likelihood of stomach irritation.","must":["salma","omar","food"]},
 {"id":"summary_1","kind":"summarize","source":"Aster Bakery opened at 6 a.m. on Friday. By noon it had sold 240 loaves of bread. A power outage then stopped the ovens for two hours. The bakery reopened production at 2 p.m. after an electrician restored power.","prompt":"Summarize the following text concisely while preserving the key facts: Aster Bakery opened at 6 a.m. on Friday. By noon it had sold 240 loaves of bread. A power outage then stopped the ovens for two hours. The bakery reopened production at 2 p.m. after an electrician restored power.","must":["aster","240","power"]},
 {"id":"summary_2","kind":"summarize","source":"The Luma research team tested three water filters. Filter A removed 91 percent of the contaminant, Filter B removed 76 percent, and Filter C removed 88 percent. Because Filter A performed best, the team selected it for the next experiment.","prompt":"Write a brief faithful summary: The Luma research team tested three water filters. Filter A removed 91 percent of the contaminant, Filter B removed 76 percent, and Filter C removed 88 percent. Because Filter A performed best, the team selected it for the next experiment.","must":["luma","91","filter a"]},
 {"id":"summary_3","kind":"summarize","source":"Kareem left Qena at 7:10 in the morning by bus. Heavy traffic delayed the trip by 35 minutes. He reached Luxor at 10:25 and immediately called his sister to tell her he had arrived safely.","prompt":"Summarize this passage in one concise sentence while preserving the important information: Kareem left Qena at 7:10 in the morning by bus. Heavy traffic delayed the trip by 35 minutes. He reached Luxor at 10:25 and immediately called his sister to tell her he had arrived safely.","must":["kareem","qena","luxor"]},
 {"id":"story_1","kind":"story","prompt":"Write a short story of at least 35 words about a robot named Nilo who loses a red key, asks a baker named Sana for help, finds the key under a blue cart, and ends happily.","must":["nilo","sana","key","cart"],"min_words":35},
 {"id":"story_2","kind":"story","prompt":"Write a short story of at least 35 words about Lira, a young astronomer, finding a broken telescope on a hill, repairing it with her friend Basim, and seeing a comet that night. End positively.","must":["lira","basim","telescope","comet"],"min_words":35},
 {"id":"story_3","kind":"story","prompt":"Write a short story of at least 35 words about a dog named Rafi carrying a lost green scarf back to its owner Hana after following footprints through a market. The ending must be happy.","must":["rafi","hana","scarf","market"],"min_words":35},
]

def norm(s): return re.sub(r"\s+"," ",str(s or "")).strip().lower()
def words(s): return [x for x in re.split(r"\s+",str(s or "").strip()) if x]
def avg_word_len(s):
    ws=[re.sub(r"[^A-Za-z]","",x) for x in words(s)]
    ws=[x for x in ws if x]
    return sum(map(len,ws))/len(ws) if ws else 0.0
def contains_all(text,items):
    n=norm(text)
    return all(norm(x) in n for x in items)

def screen(t,out):
    r={"nonempty":bool(norm(out)),"must_preserved":contains_all(out,t["must"])}
    ow=len(words(out))
    if t["kind"]=="paraphrase":
        sw=len(words(t["source"]))
        r["changed"]=norm(out)!=norm(t["source"])
        r["length_reasonable"]=ow>=max(4,int(sw*0.45)) and ow<=int(sw*1.55+0.999)
        r["pass"]=r["nonempty"] and r["must_preserved"] and r["changed"] and r["length_reasonable"]
    elif t["kind"]=="simplify":
        sw=len(words(t["source"]))
        r["not_longer"]=ow<=sw+3
        r["lexically_not_harder"]=avg_word_len(out)<=avg_word_len(t["source"])+0.35
        r["pass"]=r["nonempty"] and r["must_preserved"] and r["not_longer"] and r["lexically_not_harder"]
    elif t["kind"]=="summarize":
        sw=len(words(t["source"]))
        r["compressed"]=ow<=int(sw*0.78)
        r["pass"]=r["nonempty"] and r["must_preserved"] and r["compressed"]
    else:
        r["long_enough"]=ow>=int(t.get("min_words",35))
        r["pass"]=r["nonempty"] and r["must_preserved"] and r["long_enough"]
    r["output_words"]=ow
    return r

def generate(prompt,max_tokens):
    payload={
      "model":MODEL,
      "messages":[
        {"role":"system","content":"Answer the user's visible request faithfully and directly. Preserve requested meaning, facts, entities, and task intent. For paraphrase, simplify, summarize, or story requests, perform the task and return only the final answer."},
        {"role":"user","content":prompt},
      ],
      "temperature":0,
      "max_tokens":max_tokens,
      "stream":False,
    }
    req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=240) as resp:
        data=json.loads(resp.read().decode("utf-8","replace"))
    choices=data.get("choices") or []
    assert len(choices)==1,data
    msg=choices[0].get("message") or {}
    assert not msg.get("tool_calls"),data
    text=str(msg.get("content") or "").strip()
    assert text,data
    return text

rows=[]
for task in TASKS:
    output=generate(task["prompt"],180 if task["kind"]=="story" else 100)
    row={"id":task["id"],"kind":task["kind"],"output":output,"screen":screen(task,output)}
    rows.append(row)
    print("SEMANTIC_SCREEN_CASE="+json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)

category={}
for kind in ("paraphrase","simplify","summarize","story"):
    xs=[x for x in rows if x["kind"]==kind]
    category[kind]={"passed":sum(1 for x in xs if x["screen"]["pass"]),"total":len(xs)}
passes_minimum=all(x["passed"]>=2 for x in category.values())
receipt={
 "schema":"PROJECT_BRAIN_QWEN35_9B_Q4_SEMANTIC_SEED_SCREEN_V1",
 "status":"PUBLIC_NONTERMINAL_SCREEN_COMPLETE",
 "model_alias":MODEL,
 "model_file":"Qwen3.5-9B-M-TS-Q4_K_M.gguf",
 "model_bytes":5060174144,
 "model_sha256":"f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
 "llama_cpp_commit":"bec4772f6a2527d371557b5d2032641e5ff7619c",
 "task_count":len(rows),
 "category":category,
 "passes_minimum_screen":passes_minimum,
 "rows":rows,
 "terminal_case_exposure":0,
 "incremental_spend_usd":0,
 "hard_nonclaims":[
   "SCREENING_ONLY__NOT_A_LIVEBENCH_SCORE",
   "NO_OPUS55_NONINFERIORITY_PROOF",
   "NO_TERMINAL_CASE_DATA_USED",
   "PASS_DOES_NOT_PROVE_FULL_SEMANTIC_EQUIVALENCE_OR_FACTUALITY",
   "FAIL_DOES_NOT_PROVE_NO_USEFUL_CAPABILITY_EXISTS"
 ]
}
open("qwen35_9b_q4_semantic_screen_receipt.json","w",encoding="utf-8").write(json.dumps(receipt,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
print("SEMANTIC_SCREEN_RESULT="+json.dumps({k:v for k,v in receipt.items() if k!="rows"},sort_keys=True),flush=True)
