import json, math, statistics, time
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from bounded_semantic_decomposer import decompose as bounded_decompose
from explicit_compound_requirement_decomposer import decompose_explicit_compound
from explicit_definition_reference_graph import compile_reference_graph

PROBE=json.loads(Path("m0a_olmo_contrastive_dev.json").read_text())
REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"


def conditional_mean_logprob(model,tok,source,candidate):
    prompt=source+"\nResolution:"
    p=tok(prompt,add_special_tokens=False)["input_ids"]
    c=tok(candidate,add_special_tokens=False)["input_ids"]
    if not p or not c:
        raise RuntimeError("empty tokenization")
    ids=torch.tensor([p+c],dtype=torch.long)
    with torch.inference_mode():
        logits=model(input_ids=ids).logits[0]
        lp=torch.log_softmax(logits,dim=-1)
    vals=[]
    start=len(p)
    for j,token_id in enumerate(c,start=start):
        vals.append(float(lp[j-1,token_id]))
    return sum(vals)/len(vals),len(vals)


def det_baseline(source):
    b=bounded_decompose(source)
    c=decompose_explicit_compound(source)
    d=compile_reference_graph(source)
    contextual_resolution=False
    if d.get("references"):
        contextual_resolution=True
    return {
        "bounded_status":b.get("status"),
        "bounded_errors":b.get("errors"),
        "compound_status":c.get("status"),
        "compound_error":c.get("error"),
        "definition_status":d.get("status"),
        "definition_reference_count":len(d.get("references") or []),
        "contextual_resolution":contextual_resolution,
    }


path=snapshot_download(
    repo_id=REPO,
    revision=REV,
    local_dir="/tmp/olmo2_1b_m0a",
    allow_patterns=["*.json","*.txt","*.model","*.safetensors"],
)
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()

rows=[]
for case in PROBE["cases"]:
    source=case["source"]
    correct,ctok=conditional_mean_logprob(model,tok,source,case["correct"])
    wrong,wtok=conditional_mean_logprob(model,tok,source,case["wrong"])
    margin=correct-wrong
    rows.append({
        "id":case["id"],
        "correct_mean_logprob":correct,
        "wrong_mean_logprob":wrong,
        "margin":margin,
        "correct_token_count":ctok,
        "wrong_token_count":wtok,
        "correct_preferred":margin>0,
        "deterministic_baseline":det_baseline(source),
    })

amb=PROBE["ambiguity_diagnostic"]
amb_scores=[]
for cand in amb["candidates"]:
    score,n=conditional_mean_logprob(model,tok,amb["source"],cand)
    amb_scores.append({"candidate":cand,"mean_logprob":score,"token_count":n})
amb_scores.sort(key=lambda x:x["mean_logprob"],reverse=True)

hits=sum(1 for x in rows if x["correct_preferred"])
margins=[x["margin"] for x in rows]
result={
    "schema":"PROJECT_BRAIN_M0A_OLMO_CONTRASTIVE_DEV_RESULT_V1",
    "probe_schema":PROBE["schema"],
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "case_count":len(rows),
    "correct_preference_count":hits,
    "accuracy":hits/len(rows),
    "mean_margin":statistics.mean(margins),
    "median_margin":statistics.median(margins),
    "min_margin":min(margins),
    "max_margin":max(margins),
    "classification":"SIGNAL_PRESENT" if hits>=5 and statistics.mean(margins)>0 else "WEAK_OR_ABSENT",
    "rows":rows,
    "ambiguity_diagnostic":{
        "id":amb["id"],
        "scores":amb_scores,
        "rule":"DONOR_PREFERENCE_HAS_ZERO_TERMINAL_AUTHORITY__AMBIGUITY_REMAINS_FAIL_CLOSED",
    },
    "heldout_cases_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(result,sort_keys=True))
