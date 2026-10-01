#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, os, re, statistics, sys, time
from pathlib import Path
from typing import Any
import torch
from huggingface_hub import HfApi
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE=Path(__file__).resolve().parent
EPISODES_PATH=HERE/"episodes.json"
ROUTER_PATH=HERE/"cognitive_tool_router.py"
RESULT_PATH=HERE/"result.json"
MODEL_ID="pipizhao/SkillRouter-Reranker-0.6B"

spec=importlib.util.spec_from_file_location("c3_router",ROUTER_PATH)
router=importlib.util.module_from_spec(spec); sys.modules[spec.name]=router
assert spec.loader is not None; spec.loader.exec_module(router)

def lexical_scorer(query, descriptions):
    q=set(re.findall(r"[a-z0-9]+",query.lower()))
    out=[]
    for text in descriptions:
        t=set(re.findall(r"[a-z0-9]+",text.lower()))
        out.append(len(q&t)/max(1,len(q|t)) if (q or t) else 0.0)
    return out

def execute(route_id,p):
    if route_id=="sum_numbers": return str(round(sum(p["numbers"]),10))
    if route_id=="mean_numbers": return str(float(sum(p["numbers"])/len(p["numbers"])))
    if route_id=="median_numbers": return str(float(statistics.median(p["numbers"])))
    if route_id=="max_number": return str(max(p["numbers"]))
    if route_id=="sort_numbers": return ",".join(str(x) for x in sorted(p["numbers"]))
    if route_id=="unique_items": return ",".join(dict.fromkeys(p["items"]))
    if route_id=="sort_text": return ",".join(sorted(p["items"]))
    if route_id=="count_words": return str(len(p["text"].split()))
    if route_id=="count_lines": return str(len(p["text"].splitlines()))
    if route_id=="uppercase_text": return p["text"].upper()
    if route_id=="reverse_text": return p["text"][::-1]
    if route_id=="basename_path": return os.path.basename(p["path"])
    if route_id=="extension_path": return os.path.splitext(p["path"])[1]
    if route_id=="json_key": return str(p["object"][p["key"]])
    if route_id=="km_to_miles": return f'{p["km"]*0.621371:.5f}'
    if route_id=="c_to_f": return str(float(p["celsius"]*9/5+32))
    if route_id=="sha256_text": return hashlib.sha256(p["text"].encode()).hexdigest()
    if route_id=="dropbox_search": return "FOUND:"+p["text"]
    if route_id=="drive_search": return "DRIVE:"+p["text"]
    if route_id=="web_search": return "WEB:"+p["text"]
    if route_id=="local_file_search": return "LOCAL:"+p["text"]
    raise KeyError(route_id)

def run_episode(ep, scorer):
    routes=[router.ToolRoute(**r) for r in ep["routes"]]
    t0=time.perf_counter()
    d=router.select_route(
        ep["query"],routes,scorer,
        required_provider=ep.get("required_provider"),
        allowed_route_ids=set(ep["allowed_route_ids"]) if ep.get("allowed_route_ids") else None,
    )
    ms=(time.perf_counter()-t0)*1000
    expected_status=ep.get("expected_status","SELECT")
    if d.status=="ESCALATE":
        output="ESCALATE"
        ok=expected_status=="ESCALATE" and output==ep["expected_output"]
    else:
        try: output=execute(d.route_id,ep["payload"])
        except Exception as exc: output=f"TOOL_ERROR:{type(exc).__name__}"
        ok=expected_status=="SELECT" and d.route_id==ep.get("expected_route") and output==ep["expected_output"]
    return {
      "id":ep["id"],"selected_route":d.route_id,"decision_status":d.status,
      "eligible_route_ids":list(d.eligible_route_ids),"terminal_success":bool(ok),
      "routing_latency_ms":ms,
      "semantic_choice_required":d.status=="SELECT" and len(d.eligible_route_ids)>1,
    }

def aggregate(rows):
    sem=[r for r in rows if r["semantic_choice_required"]]
    det=[r for r in rows if not r["semantic_choice_required"]]
    return {
      "episodes":len(rows),
      "terminal_successes":sum(r["terminal_success"] for r in rows),
      "terminal_success_rate":sum(r["terminal_success"] for r in rows)/len(rows),
      "semantic_choice_episodes":len(sem),
      "semantic_terminal_success_rate":sum(r["terminal_success"] for r in sem)/len(sem) if sem else None,
      "deterministic_filter_episodes":len(det),
      "deterministic_filter_success_rate":sum(r["terminal_success"] for r in det)/len(det) if det else None,
      "mean_routing_latency_ms":sum(r["routing_latency_ms"] for r in rows)/len(rows),
      "failures":[r["id"] for r in rows if not r["terminal_success"]],
    }

def main():
    episodes=json.loads(EPISODES_PATH.read_text())["episodes"]
    rev=HfApi().model_info(MODEL_ID).sha
    tok=AutoTokenizer.from_pretrained(MODEL_ID,padding_side="left")
    if tok.pad_token_id is None: tok.pad_token=tok.eos_token
    model=AutoModelForCausalLM.from_pretrained(
        MODEL_ID,torch_dtype=torch.float32,low_cpu_mem_usage=True
    ).eval()
    yes=tok.convert_tokens_to_ids("yes"); no=tok.convert_tokens_to_ids("no")
    prefix=(
      '<|im_start|>system\nJudge whether the Document meets the requirements '
      'based on the Query and the Instruct provided. Note that the answer can '
      'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
    )
    suffix='<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
    pfx=tok.encode(prefix,add_special_tokens=False); sfx=tok.encode(suffix,add_special_tokens=False)
    inst="Given a task description, judge whether the skill document is relevant and useful for completing the task"

    def batched_scorer(query, descriptions):
        seqs=[]
        for desc in descriptions:
            prompt=f"<Instruct>: {inst}\n\n<Query>: {query}\n\n<Document>: {desc}"
            mid=tok(prompt,padding=False,truncation=True,max_length=2048-len(pfx)-len(sfx),return_attention_mask=False)["input_ids"]
            seqs.append(pfx+mid+sfx)
        batch=tok.pad({"input_ids":seqs},padding=True,return_tensors="pt")
        with torch.no_grad():
            logits=model(input_ids=batch["input_ids"],attention_mask=batch["attention_mask"]).logits[:,-1,:]
        return [float(x) for x in (logits[:,yes]-logits[:,no]).tolist()]

    baseline_rows=[run_episode(ep,lexical_scorer) for ep in episodes]
    batch_rows=[run_episode(ep,batched_scorer) for ep in episodes]
    baseline=aggregate(baseline_rows); batch=aggregate(batch_rows)
    result={
      "schema":"PROJECT_BRAIN_C3_SKILLROUTER_BATCHED_SPENT_SCREEN_RESULT_V1",
      "status":"SPENT_EPISODE_OPTIMIZATION_SCREEN__ZERO_CAPABILITY_CREDIT",
      "model":MODEL_ID,"model_revision":rev,
      "episodes_blob":"439a13dfd5824117e3d50a7a5673056cbc745dfd",
      "baseline":baseline,"skillrouter_batched":batch,
      "terminal_success_delta":batch["terminal_success_rate"]-baseline["terminal_success_rate"],
      "semantic_terminal_success_delta":batch["semantic_terminal_success_rate"]-baseline["semantic_terminal_success_rate"],
      "same_expected_prior_skillrouter_success_rate":0.95,
      "latency_vs_prior_sequential_fraction":batch["mean_routing_latency_ms"]/2436.3967482000007,
      "fresh_evidence_authorized":bool(
        batch["terminal_success_rate"]>baseline["terminal_success_rate"]
        and batch["semantic_terminal_success_rate"]>baseline["semantic_terminal_success_rate"]
      ),
      "baseline_rows":baseline_rows,"skillrouter_batched_rows":batch_rows,
      "capability_credit_delta":0
    }
    RESULT_PATH.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if not k.endswith("_rows")},indent=2))

if __name__=="__main__": main()
