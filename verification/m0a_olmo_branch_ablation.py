import json, statistics
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE=json.loads(Path("verification/m0a_olmo_contrastive_dev.json").read_text())
REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"
LAYERS=[1,3,4,6,11]

def mean_logprob(model,tok,source,candidate):
    prompt=source+"\nResolution:"
    p=tok(prompt,add_special_tokens=False)["input_ids"]
    c=tok(candidate,add_special_tokens=False)["input_ids"]
    ids=torch.tensor([p+c],dtype=torch.long)
    with torch.inference_mode():
        logits=model(input_ids=ids,use_cache=False).logits[0]
        lp=torch.log_softmax(logits,dim=-1)
    vals=[float(lp[j-1,tid]) for j,tid in enumerate(c,start=len(p))]
    return sum(vals)/len(vals)

def evaluate(model,tok):
    rows=[]
    for case in PROBE["cases"]:
        a=mean_logprob(model,tok,case["source"],case["correct"])
        b=mean_logprob(model,tok,case["source"],case["wrong"])
        rows.append({"id":case["id"],"margin":a-b,"correct_preferred":a>b})
    return {
        "correct_count":sum(x["correct_preferred"] for x in rows),
        "accuracy":sum(x["correct_preferred"] for x in rows)/len(rows),
        "mean_margin":statistics.mean(x["margin"] for x in rows),
        "rows":rows,
    }

def zero_primary_output(module,args,output):
    if isinstance(output,torch.Tensor):
        return torch.zeros_like(output)
    if isinstance(output,tuple) and output and isinstance(output[0],torch.Tensor):
        return (torch.zeros_like(output[0]),)+output[1:]
    raise RuntimeError("unsupported branch output type: "+type(output).__name__)

path=snapshot_download(
    repo_id=REPO,revision=REV,local_dir="/tmp/olmo2_1b_branch_ablate",
    allow_patterns=["*.json","*.txt","*.model","*.safetensors"],
)
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()
baseline=evaluate(model,tok)
base_by={x["id"]:x for x in baseline["rows"]}

rows=[]
for layer_id in LAYERS:
    layer=model.model.layers[layer_id]
    for branch_name,module in [("SELF_ATTENTION_OUTPUT",layer.self_attn),("MLP_OUTPUT",layer.mlp)]:
        handle=module.register_forward_hook(zero_primary_output)
        try:
            ab=evaluate(model,tok)
        finally:
            handle.remove()
        flips=[
            x["id"] for x in ab["rows"]
            if base_by[x["id"]]["correct_preferred"] and not x["correct_preferred"]
        ]
        loss=baseline["mean_margin"]-ab["mean_margin"]
        rows.append({
            "layer":layer_id,
            "branch":branch_name,
            "ablated_correct_count":ab["correct_count"],
            "ablated_accuracy":ab["accuracy"],
            "ablated_mean_margin":ab["mean_margin"],
            "baseline_minus_ablated_mean_margin":loss,
            "baseline_correct_to_wrong_flips":flips,
            "material":loss>=0.10 or bool(flips),
            "per_case_margin_delta":{
                x["id"]:base_by[x["id"]]["margin"]-x["margin"] for x in ab["rows"]
            },
        })

rows.sort(key=lambda x:(-x["baseline_minus_ablated_mean_margin"],x["layer"],x["branch"]))
out={
    "schema":"PROJECT_BRAIN_M0A_OLMO_BRANCH_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "admissible_layers":LAYERS,
    "baseline":baseline,
    "intervention":"ZERO_ONLY_SELF_ATTENTION_OR_MLP_BRANCH_OUTPUT_IN_ONE_ADMISSIBLE_LAYER",
    "material_rule":"BASELINE_MEAN_MARGIN_MINUS_ABLATED_MEAN_MARGIN_GE_0_10_OR_ANY_BASELINE_CORRECT_CASE_FLIPS_WRONG",
    "ranked_branch_ablation":rows,
    "material_branches":[
        {"layer":x["layer"],"branch":x["branch"]} for x in rows if x["material"]
    ],
    "classification":"MATERIAL_BRANCHES_LOCALIZED" if any(x["material"] for x in rows) else "INTERACTION_OR_DISTRIBUTED_WITHIN_MATERIAL_LAYERS",
    "heldout_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
