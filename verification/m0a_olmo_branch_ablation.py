import json, statistics
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE=json.loads(Path("m0a_olmo_contrastive_dev.json").read_text())
REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"
CANDIDATE_LAYERS=[1,3,4,6,11]


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


def zero_first_tensor(_module,_inputs,output):
    if torch.is_tensor(output):
        return torch.zeros_like(output)
    if isinstance(output,tuple) and output and torch.is_tensor(output[0]):
        return (torch.zeros_like(output[0]),)+tuple(output[1:])
    if isinstance(output,list) and output and torch.is_tensor(output[0]):
        return [torch.zeros_like(output[0])]+list(output[1:])
    raise RuntimeError("UNSUPPORTED_BRANCH_OUTPUT:"+type(output).__name__)


path=snapshot_download(
    repo_id=REPO,revision=REV,local_dir="/tmp/olmo2_1b_branch_ablate",
    allow_patterns=["*.json","*.txt","*.model","*.safetensors"],
)
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()
layers=model.model.layers
baseline=evaluate(model,tok)
base_by={x["id"]:x for x in baseline["rows"]}
results=[]

for layer_idx in CANDIDATE_LAYERS:
    if layer_idx>=len(layers):
        raise RuntimeError(f"LAYER_OUT_OF_RANGE:{layer_idx}")
    layer=layers[layer_idx]
    branches=[]
    if hasattr(layer,"self_attn"):
        branches.append(("attention",layer.self_attn))
    else:
        raise RuntimeError(f"NO_SELF_ATTN:{layer_idx}")
    if hasattr(layer,"mlp"):
        branches.append(("mlp",layer.mlp))
    else:
        raise RuntimeError(f"NO_MLP:{layer_idx}")

    for branch_name,module in branches:
        hook=module.register_forward_hook(zero_first_tensor)
        try:
            ab=evaluate(model,tok)
        finally:
            hook.remove()
        flips=[
            x["id"] for x in ab["rows"]
            if base_by[x["id"]]["correct_preferred"] and not x["correct_preferred"]
        ]
        rescues=[
            x["id"] for x in ab["rows"]
            if not base_by[x["id"]]["correct_preferred"] and x["correct_preferred"]
        ]
        drop=baseline["mean_margin"]-ab["mean_margin"]
        results.append({
            "layer":layer_idx,
            "branch":branch_name,
            "ablated_accuracy":ab["accuracy"],
            "ablated_correct_count":ab["correct_count"],
            "ablated_mean_margin":ab["mean_margin"],
            "baseline_minus_ablated_mean_margin":drop,
            "baseline_correct_to_wrong_flips":flips,
            "baseline_wrong_to_correct_rescues":rescues,
            "material":drop>=0.10 or bool(flips),
            "rows":ab["rows"],
        })

results.sort(key=lambda x:x["baseline_minus_ablated_mean_margin"],reverse=True)
material=[x for x in results if x["material"]]
out={
    "schema":"PROJECT_BRAIN_M0A_OLMO_ATTENTION_MLP_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "candidate_layers":CANDIDATE_LAYERS,
    "baseline":baseline,
    "ranked_branch_ablation":results,
    "material_branches":[{"layer":x["layer"],"branch":x["branch"]} for x in material],
    "classification":"MATERIAL_SUBMODULE_CANDIDATES_FOUND" if material else "DISTRIBUTED_BEYOND_BRANCH_GRANULARITY",
    "heldout_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
