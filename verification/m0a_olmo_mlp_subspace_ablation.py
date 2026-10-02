import json, statistics
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE=json.loads(Path("verification/m0a_olmo_contrastive_dev.json").read_text())
REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"
LAYERS=[1,11]
GROUPS=8

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

def get_down_proj(mlp):
    for name in ("down_proj","ff_out","output_proj"):
        m=getattr(mlp,name,None)
        if m is not None:
            return m,name
    raise RuntimeError("no supported MLP down projection found; attrs="+",".join(sorted(x for x in dir(mlp) if not x.startswith("_"))))

def group_bounds(width, group, groups):
    lo=(width*group)//groups
    hi=(width*(group+1))//groups
    return lo,hi

def make_zero_group_hook(group):
    def hook(module,args):
        if not args or not isinstance(args[0],torch.Tensor):
            raise RuntimeError("unexpected down-projection input")
        x=args[0]
        lo,hi=group_bounds(x.shape[-1],group,GROUPS)
        y=x.clone()
        y[...,lo:hi]=0
        return (y,)+tuple(args[1:])
    return hook

path=snapshot_download(
    repo_id=REPO,revision=REV,local_dir="/tmp/olmo2_1b_mlp_subspace",
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
    down,down_name=get_down_proj(layer.mlp)
    # Infer exact intermediate width from a single real pre-hook observation.
    captured={}
    def capture(module,args):
        captured["width"]=int(args[0].shape[-1])
    h=down.register_forward_pre_hook(capture)
    try:
        _=mean_logprob(model,tok,PROBE["cases"][0]["source"],PROBE["cases"][0]["correct"])
    finally:
        h.remove()
    width=captured["width"]

    for group in range(GROUPS):
        lo,hi=group_bounds(width,group,GROUPS)
        handle=down.register_forward_pre_hook(make_zero_group_hook(group))
        try:
            ab=evaluate(model,tok)
        finally:
            handle.remove()
        flips=[
            x["id"] for x in ab["rows"]
            if base_by[x["id"]]["correct_preferred"] and not x["correct_preferred"]
        ]
        loss=baseline["mean_margin"]-ab["mean_margin"]
        useful_losses=[
            base_by[x["id"]]["margin"]-x["margin"]
            for x in ab["rows"] if base_by[x["id"]]["correct_preferred"]
        ]
        mean_useful_loss=statistics.mean(useful_losses) if useful_losses else 0.0
        rows.append({
            "layer":layer_id,
            "down_projection_attr":down_name,
            "intermediate_width":width,
            "group":group,
            "channel_start":lo,
            "channel_end_exclusive":hi,
            "channel_count":hi-lo,
            "ablated_correct_count":ab["correct_count"],
            "ablated_accuracy":ab["accuracy"],
            "ablated_mean_margin":ab["mean_margin"],
            "baseline_minus_ablated_mean_margin":loss,
            "baseline_correct_mean_margin_loss":mean_useful_loss,
            "baseline_correct_to_wrong_flips":flips,
            "material":loss>=0.10 or bool(flips),
            "useful_material":mean_useful_loss>=0.10 or bool(flips),
            "per_case_margin_delta":{
                x["id"]:base_by[x["id"]]["margin"]-x["margin"] for x in ab["rows"]
            },
        })

rows.sort(key=lambda x:(-x["baseline_correct_mean_margin_loss"],-x["baseline_minus_ablated_mean_margin"],x["layer"],x["group"]))
out={
    "schema":"PROJECT_BRAIN_M0A_OLMO_MLP_SUBSPACE_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "layers":LAYERS,
    "group_count":GROUPS,
    "baseline":baseline,
    "intervention":"ZERO_ONE_CONTIGUOUS_NEAR_EQUAL_GROUP_OF_POST_GATING_MLP_INTERMEDIATE_CHANNELS_AT_DOWN_PROJECTION_INPUT",
    "material_rule":"BASELINE_MEAN_MARGIN_MINUS_ABLATED_MEAN_MARGIN_GE_0_10_OR_ANY_BASELINE_CORRECT_CASE_FLIPS_WRONG",
    "useful_material_rule":"MEAN_MARGIN_LOSS_OVER_BASELINE_CORRECT_CASES_GE_0_10_OR_ANY_BASELINE_CORRECT_CASE_FLIPS_WRONG",
    "ranked_group_ablation":rows,
    "material_groups":[
        {"layer":x["layer"],"group":x["group"],"channel_start":x["channel_start"],"channel_end_exclusive":x["channel_end_exclusive"]}
        for x in rows if x["material"]
    ],
    "useful_material_groups":[
        {"layer":x["layer"],"group":x["group"],"channel_start":x["channel_start"],"channel_end_exclusive":x["channel_end_exclusive"]}
        for x in rows if x["useful_material"]
    ],
    "classification":"LOCALIZED_GROUPS_FOUND" if any(x["useful_material"] for x in rows) else "DISTRIBUTED_OR_NO_USEFUL_GROUP_AT_EIGHT_WAY_GRANULARITY",
    "heldout_exposed":0,
    "fresh_terminal_evidence_consumed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
