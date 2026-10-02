import json, statistics, types
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE=json.loads(Path("m0a_olmo_contrastive_dev.json").read_text())
REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"


def mean_logprob(model,tok,source,candidate):
    prompt=source+"\nResolution:"
    p=tok(prompt,add_special_tokens=False)["input_ids"]
    c=tok(candidate,add_special_tokens=False)["input_ids"]
    ids=torch.tensor([p+c],dtype=torch.long)
    with torch.inference_mode():
        logits=model(input_ids=ids,use_cache=False).logits[0]
        lp=torch.log_softmax(logits,dim=-1)
    start=len(p)
    vals=[float(lp[j-1,tid]) for j,tid in enumerate(c,start=start)]
    return sum(vals)/len(vals)


def evaluate(model,tok):
    rows=[]
    for case in PROBE["cases"]:
        a=mean_logprob(model,tok,case["source"],case["correct"])
        b=mean_logprob(model,tok,case["source"],case["wrong"])
        rows.append({"id":case["id"],"margin":a-b,"correct_preferred":a>b})
    return {
        "accuracy":sum(x["correct_preferred"] for x in rows)/len(rows),
        "correct_count":sum(x["correct_preferred"] for x in rows),
        "mean_margin":statistics.mean(x["margin"] for x in rows),
        "rows":rows,
    }


path=snapshot_download(
    repo_id=REPO,revision=REV,local_dir="/tmp/olmo2_1b_layer_ablate",
    allow_patterns=["*.json","*.txt","*.model","*.safetensors"],
)
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()
layers=model.model.layers
baseline=evaluate(model,tok)
results=[]
for i,layer in enumerate(layers):
    original=layer.forward
    def identity(self,hidden_states,*args,**kwargs):
        return hidden_states
    layer.forward=types.MethodType(identity,layer)
    try:
        ab=evaluate(model,tok)
    finally:
        layer.forward=original
    base_by={x["id"]:x for x in baseline["rows"]}
    flips=[
        x["id"] for x in ab["rows"]
        if base_by[x["id"]]["correct_preferred"] and not x["correct_preferred"]
    ]
    effect=baseline["mean_margin"]-ab["mean_margin"]
    results.append({
        "layer":i,
        "ablated_accuracy":ab["accuracy"],
        "ablated_correct_count":ab["correct_count"],
        "ablated_mean_margin":ab["mean_margin"],
        "baseline_minus_ablated_mean_margin":effect,
        "baseline_correct_to_wrong_flips":flips,
        "material":effect>=0.10 or bool(flips),
        "rows":ab["rows"],
    })
results.sort(key=lambda x:x["baseline_minus_ablated_mean_margin"],reverse=True)
out={
    "schema":"PROJECT_BRAIN_M0A_OLMO_LAYER_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "layer_count":len(layers),
    "baseline":baseline,
    "ranked_layer_ablation":results,
    "material_layers":[x["layer"] for x in results if x["material"]],
    "classification":"MATERIAL_LAYER_CANDIDATES_FOUND" if any(x["material"] for x in results) else "DISTRIBUTED_AT_LAYER_GRANULARITY",
    "heldout_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
