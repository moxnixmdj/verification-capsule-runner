import json, statistics
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE=json.loads(Path("m0a_olmo_contrastive_dev.json").read_text())
PROTOCOL=json.loads(Path("m0a_olmo_layer_causal_localization.json").read_text())
REPO=PROTOCOL["donor"]["repository"]
REV=PROTOCOL["donor"]["resolved_hf_sha"]


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
    return sum(vals)/len(vals)


def score_cases(model,tok):
    rows=[]
    for case in PROBE["cases"]:
        correct=conditional_mean_logprob(model,tok,case["source"],case["correct"])
        wrong=conditional_mean_logprob(model,tok,case["source"],case["wrong"])
        margin=correct-wrong
        rows.append({"id":case["id"],"margin":margin,"correct_preferred":margin>0})
    return rows


def locate_layers(model):
    candidates=[
        ("model.layers", getattr(getattr(model,"model",None),"layers",None)),
        ("model.transformer.blocks", getattr(getattr(getattr(model,"model",None),"transformer",None),"blocks",None)),
        ("transformer.blocks", getattr(getattr(model,"transformer",None),"blocks",None)),
        ("model.blocks", getattr(getattr(model,"model",None),"blocks",None)),
    ]
    for name,layers in candidates:
        if layers is not None and hasattr(layers,"__len__") and len(layers)>0:
            return name,layers
    raise RuntimeError("unable to locate decoder layer stack")


def identity_layer_hook(module,inputs,output):
    if not inputs:
        raise RuntimeError("decoder layer received no positional hidden state")
    hidden=inputs[0]
    if torch.is_tensor(output):
        return hidden
    if isinstance(output,tuple):
        return (hidden,)+tuple(output[1:])
    raise RuntimeError("unsupported decoder layer output type: "+type(output).__name__)


path=snapshot_download(
    repo_id=REPO,
    revision=REV,
    local_dir="/tmp/olmo2_1b_m0a_layer",
    allow_patterns=["*.json","*.txt","*.model","*.safetensors"],
)
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()
layer_path,layers=locate_layers(model)

baseline=score_cases(model,tok)
baseline_by={x["id"]:x for x in baseline}
baseline_mean=statistics.mean(x["margin"] for x in baseline)
baseline_hits=sum(x["correct_preferred"] for x in baseline)

ablations=[]
for idx,layer in enumerate(layers):
    handle=layer.register_forward_hook(identity_layer_hook)
    try:
        rows=score_cases(model,tok)
    finally:
        handle.remove()
    mean_margin=statistics.mean(x["margin"] for x in rows)
    hits=sum(x["correct_preferred"] for x in rows)
    drops=[baseline_by[x["id"]]["margin"]-x["margin"] for x in rows]
    flipped=[
        x["id"] for x in rows
        if baseline_by[x["id"]]["correct_preferred"] and not x["correct_preferred"]
    ]
    delta=baseline_mean-mean_margin
    material=(delta>=0.10) or bool(flipped)
    ablations.append({
        "layer_index":idx,
        "correct_preference_count":hits,
        "mean_margin":mean_margin,
        "baseline_minus_ablated_mean_margin":delta,
        "baseline_correct_flipped_wrong":flipped,
        "material":material,
        "per_case":[
            {
                "id":x["id"],
                "ablated_margin":x["margin"],
                "baseline_margin":baseline_by[x["id"]]["margin"],
                "baseline_minus_ablated_margin":baseline_by[x["id"]]["margin"]-x["margin"],
                "ablated_correct_preferred":x["correct_preferred"],
            }
            for x in rows
        ],
    })

ranked=sorted(
    ablations,
    key=lambda x:(-x["baseline_minus_ablated_mean_margin"],x["layer_index"])
)
material=[x["layer_index"] for x in ranked if x["material"]]
result={
    "schema":"PROJECT_BRAIN_M0A_OLMO_LAYER_CAUSAL_LOCALIZATION_RESULT_V1",
    "protocol_schema":PROTOCOL["schema"],
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "layer_stack_path":layer_path,
    "layer_count":len(layers),
    "baseline_correct_preference_count":baseline_hits,
    "baseline_mean_margin":baseline_mean,
    "baseline_rows":baseline,
    "ablations":ablations,
    "material_layers_ranked":material,
    "classification":"MATERIAL_LAYERS_FOUND" if material else "DISTRIBUTED_AT_LAYER_GRANULARITY",
    "heldout_cases_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(result,sort_keys=True))
