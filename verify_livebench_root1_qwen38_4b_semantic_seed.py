#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL_SHA256 = "dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790"
MODEL_BYTES = 2783446304
MODEL_REVISION = "391fc7d103e3942a408def3e4f51c2f85d464417"
LLAMA_CPP_COMMIT = "0504396140d1c882f5f6ee34466a42db7ae90114"
SEED_BASE = 424200

CASES = [
    {
        "id":"PARA_1","effect":"text.paraphrase.semantic_preserving",
        "instruction":"Paraphrase the sentence without changing any facts. Use one sentence and no more than 24 words. Return only the answer. Do not show reasoning or use <think> tags.",
        "source":"Neris delivered seven amber parcels to Corin before sunrise on Tuesday.",
        "required_groups":[["neris"],["corin"],["seven","7"],["amber"],["tuesday"]],
        "max_words":24,"max_sentences":1,"min_source_change":True,
    },
    {
        "id":"PARA_2","effect":"text.paraphrase.semantic_preserving",
        "instruction":"Paraphrase the sentence without changing any facts. Use one sentence and no more than 28 words. Return only the answer. Do not show reasoning or use <think> tags.",
        "source":"The observatory postponed the Lumen-4 launch by three days because high winds crossed the ridge.",
        "required_groups":[["lumen-4","lumen 4"],["three","3"],["wind"],["ridge"],["postpon","delay"]],
        "max_words":28,"max_sentences":1,"min_source_change":True,
    },
    {
        "id":"SIMPLE_1","effect":"text.simplify.semantic_preserving",
        "instruction":"Rewrite this in simple everyday English in no more than 14 words. Preserve who did what and where. Return only the answer. Do not show reasoning or use <think> tags.",
        "source":"Following the cessation of precipitation, Mira initiated pedestrian transit toward the eastern laboratory.",
        "required_groups":[["mira"],["east","eastern"],["lab","laboratory"],["walk","went","go","headed","moved","travel"]],
        "max_words":14,"min_source_change":True,
    },
    {
        "id":"SIMPLE_2","effect":"text.simplify.semantic_preserving",
        "instruction":"Rewrite this in simple everyday English in no more than 18 words. Preserve the cause and action. Return only the answer. Do not show reasoning or use <think> tags.",
        "source":"Because the photovoltaic array ceased generating energy after dusk, Tovan activated the reserve battery.",
        "required_groups":[["tovan"],["battery"],["solar","photovoltaic"],["dusk","night","dark"],["because","so","when","after"]],
        "max_words":18,"min_source_change":True,
    },
    {
        "id":"SUM_1","effect":"text.summarize.faithful",
        "instruction":"Summarize the report in one sentence of no more than 22 words. Keep the mission result and return event. Return only the answer. Do not show reasoning or use <think> tags.",
        "source":"The Alba rover traveled twelve kilometers across the plain. Its battery fell to 41 percent. At Site K it collected a basalt sample. Alba returned to base at 18:20 without damage.",
        "required_groups":[["alba"],["basalt"],["site k","site-k"],["return","base"],["without damage","undamaged","safe"]],
        "max_words":22,"max_sentences":1,
    },
    {
        "id":"SUM_2","effect":"text.summarize.faithful",
        "instruction":"Summarize the report in one sentence of no more than 22 words. Keep the decision, reason, and new time. Return only the answer. Do not show reasoning or use <think> tags.",
        "source":"The Delta team inspected Bridge 6 at 09:00. Engineers found ice on the north joints. The team postponed the load test for safety. The replacement test is scheduled for Friday at 14:00.",
        "required_groups":[["delta"],["bridge 6","bridge-6"],["ice"],["postpon","delay"],["friday"],["14:00","2:00","2 pm","2pm"]],
        "max_words":22,"max_sentences":1,
    },
    {
        "id":"STORY_1","effect":"text.story.generate_instruction_grounded",
        "instruction":"Write exactly three short sentences. In order: Nara finds a brass key; she opens a green box with it; she gives the map inside to Ivo. Return only the story. Do not show reasoning or use <think> tags.",
        "source":"",
        "required_groups":[["nara"],["brass"],["key"],["green"],["box"],["map"],["ivo"]],
        "ordered_groups":[["nara","key"],["green","box"],["map","ivo"]],
        "exact_sentences":3,"max_words":45,
    },
    {
        "id":"STORY_2","effect":"text.story.generate_instruction_grounded",
        "instruction":"Write exactly three short sentences. In order: Aris lights a lantern; he crosses the old bridge; he uses the lantern to guide a lost dog home. Return only the story. Do not show reasoning or use <think> tags.",
        "source":"",
        "required_groups":[["aris"],["lantern"],["bridge"],["dog"],["home"]],
        "ordered_groups":[["aris","lantern"],["bridge"],["dog","home"]],
        "exact_sentences":3,"max_words":45,
    },
]

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def normalize(s: str) -> str:
    return " ".join(s.lower().strip().split())

def strip_reasoning(s: str) -> str:
    s=re.sub(r"<think>.*?</think>","",s,flags=re.I|re.S)
    if "</think>" in s.lower():
        s=re.split(r"</think>",s,flags=re.I)[-1]
    s=re.sub(r"^\s*(?:final(?: answer)?\s*[:\-]\s*)","",s,flags=re.I)
    return s.strip()

def sentence_parts(s: str) -> list[str]:
    parts=[x.strip() for x in re.split(r"(?<=[.!?])\s+",s.strip()) if x.strip()]
    return parts if parts else ([s.strip()] if s.strip() else [])

def word_count(s: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b",s,flags=re.UNICODE))

def contains_alt(text: str, alt: str) -> bool:
    return normalize(alt) in normalize(text)

def score_case(case: dict, output: str) -> dict:
    clean=strip_reasoning(output)
    checks={}
    checks["nonempty"]=bool(clean)
    checks["required_groups"]=all(any(contains_alt(clean,a) for a in group) for group in case["required_groups"])
    wc=word_count(clean)
    checks["word_limit"]=wc <= case["max_words"]
    parts=sentence_parts(clean)
    if "max_sentences" in case:
        checks["sentence_limit"]=len(parts) <= case["max_sentences"]
    if "exact_sentences" in case:
        checks["exact_sentences"]=len(parts) == case["exact_sentences"]
    if case.get("min_source_change"):
        a=normalize(case["source"]); b=normalize(clean)
        checks["not_verbatim"]=a != b
        checks["material_surface_change"]=difflib.SequenceMatcher(None,a,b).ratio() < 0.95
    if case.get("ordered_groups"):
        ordered=case["ordered_groups"]
        checks["ordered_grounding"]=len(parts)>=len(ordered) and all(
            all(contains_alt(parts[i],token) for token in required)
            for i,required in enumerate(ordered)
        )
    return {
        "id":case["id"],"effect":case["effect"],"raw_output":output,
        "scored_output":clean,"word_count":wc,"sentence_count":len(parts),
        "checks":checks,"pass":all(checks.values()),
    }

def http_json(url: str, payload: dict | None=None, timeout: int=300):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read())

def wait_server(base: str, proc: subprocess.Popen, deadline: float):
    last=None
    while time.time()<deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"LLAMA_SERVER_EXITED_{proc.returncode}")
        try:
            with urllib.request.urlopen(base+"/health",timeout=2) as r:
                if r.status==200:
                    return
        except Exception as e:
            last=repr(e)
        time.sleep(1)
    raise RuntimeError("LLAMA_SERVER_HEALTH_TIMEOUT:"+str(last))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",required=True)
    ap.add_argument("--server",required=True)
    ap.add_argument("--receipt",default="livebench_root1_qwen38_4b_semantic_seed_receipt.json")
    args=ap.parse_args()
    model=Path(args.model)
    assert model.is_file(),model
    assert model.stat().st_size==MODEL_BYTES,(model.stat().st_size,MODEL_BYTES)
    assert sha256_file(model)==MODEL_SHA256

    log=Path("llama_server_semantic_seed.log")
    with log.open("wb") as lf:
        proc=subprocess.Popen([
            args.server,"-m",str(model),"--host","127.0.0.1","--port","8080",
            "-c","4096","-t","4","-np","1","-ngl","0",
        ],stdout=lf,stderr=subprocess.STDOUT)
    rows=[]
    error=None
    try:
        base="http://127.0.0.1:8080"
        wait_server(base,proc,time.time()+240)
        models=http_json(base+"/v1/models")
        model_id=models["data"][0]["id"]
        for i,case in enumerate(CASES):
            user=case["instruction"]
            if case["source"]:
                user += "\n\nTEXT:\n" + case["source"]
            payload={
                "model":model_id,
                "messages":[{"role":"user","content":user}],
                "max_tokens":192,
                "temperature":0.6,
                "top_p":0.95,
                "seed":SEED_BASE+i,
                "chat_template_kwargs":{"enable_thinking":False},
            }
            try:
                response=http_json(base+"/v1/chat/completions",payload,timeout=420)
                content=response["choices"][0]["message"].get("content") or ""
                row=score_case(case,content)
                row["request_seed"]=SEED_BASE+i
                row["generation_error"]=None
            except Exception as e:
                row={
                    "id":case["id"],"effect":case["effect"],"raw_output":"",
                    "scored_output":"","checks":{"generation":False},"pass":False,
                    "request_seed":SEED_BASE+i,"generation_error":repr(e),
                }
            rows.append(row)
    except Exception as e:
        error=repr(e)
    finally:
        proc.terminate()
        try: proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=10)

    effects={}
    for case in CASES:
        effects.setdefault(case["effect"],[])
    for row in rows:
        effects[row["effect"]].append(bool(row["pass"]))
    effect_pass={k:(len(v)==2 and all(v)) for k,v in effects.items()}
    suite_pass=(error is None and len(rows)==len(CASES) and all(r["pass"] for r in rows) and all(effect_pass.values()))
    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PUBLIC_RUNNER_RECEIPT_V1",
        "status":"PASS" if suite_pass else "FAIL",
        "precommit":"canonical/governance/LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V1.json",
        "model":{"revision":MODEL_REVISION,"bytes":MODEL_BYTES,"sha256":MODEL_SHA256},
        "runtime":{"llama_cpp_commit":LLAMA_CPP_COMMIT,"server":"llama-server","threads":4,"ctx":4096,"parallel":1,"gpu_layers":0},
        "generation":{"attempts_per_case":1,"temperature":0.6,"top_p":0.95,"max_tokens":192,"seed_base":SEED_BASE,"adaptive_retry":False},
        "counts":{"cases_expected":len(CASES),"cases_executed":len(rows),"cases_pass":sum(bool(x.get("pass")) for x in rows)},
        "effect_pass":effect_pass,
        "suite_pass":suite_pass,
        "fatal_error":error,
        "rows":rows,
        "hard_nonclaims":[
            "NO_LIVEBENCH_THRESHOLD_SCORE_INHERITANCE",
            "NO_TERMINAL_CASE_CONTENT_OR_METADATA_USED",
            "NO_GENERAL_SEMANTIC_EQUIVALENCE_THEOREM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
            "NO_CASE_73_OR_LATER_AUTHORITY",
        ],
    }
    Path(args.receipt).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0 if suite_pass else 1

if __name__=="__main__":
    raise SystemExit(main())
