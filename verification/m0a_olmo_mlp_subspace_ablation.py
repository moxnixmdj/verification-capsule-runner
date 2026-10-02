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
useful_ids=sorted(x["id"] for x in baseline["rows"] if x["correct_preferred"])
known_failures=sorted(x["id"] for x in baseline["rows"] if not x["correct_preferred"])
baseline_useful_mean=statistics.mean(base_by[cid]["margin"] for cid in useful_ids)
rows=[]

for layer_id in LAYERS:
    mlp=model.model.layers[layer_id].mlp
    if not hasattr(mlp,"down_proj"):
        raise RuntimeError(f"layer {layer_id} MLP has no down_proj")
    width=int(mlp.down_proj.in_features)
    bounds=[]
    for g in range(GROUPS):
        lo=(width*g)//GROUPS
        hi=(width*(g+1))//GROUPS
        bounds.append((lo,hi))
    for group,(lo,hi) in enumerate(bounds):
        def make_hook(lo,hi):
            def hook(module,args):
                if not args or not isinstance(args[0],torch.Tensor):
                    raise RuntimeError("unexpected down_proj input")
                x=args[0].clone()
                x[...,lo:hi]=0
                return (x,)+tuple(args[1:])
            return hook
        handle=mlp.down_proj.register_forward_pre_hook(make_hook(lo,hi))
        try:
            ab=evaluate(model,tok)
        finally:
            handle.remove()
        ab_by={x["id"]:x for x in ab["rows"]}
        flips=[cid for cid in useful_ids if not ab_by[cid]["correct_preferred"]]
        useful_mean=statistics.mean(ab_by[cid]["margin"] for cid in useful_ids)
        useful_loss=baseline_useful_mean-useful_mean
        rows.append({
            "layer":layer_id,"group":group,"start":lo,"end":hi,"width":hi-lo,
            "ablated_correct_count":ab["correct_count"],
            "ablated_accuracy":ab["accuracy"],
            "ablated_mean_margin_all_cases":ab["mean_margin"],
            "ablated_useful_mean_margin":useful_mean,
            "baseline_useful_minus_ablated_useful_mean_margin":useful_loss,
            "useful_baseline_correct_to_wrong_flips":flips,
            "known_failure_margins":{cid:ab_by[cid]["margin"] for cid in known_failures},
            "material":useful_loss>=0.10 or bool(flips),
            "per_case_margin_delta":{x["id"]:base_by[x["id"]]["margin"]-x["margin"] for x in ab["rows"]},
        })

rows.sort(key=lambda x:(-x["baseline_useful_minus_ablated_useful_mean_margin"],x["layer"],x["group"]))
out={
    "schema":"PROJECT_BRAIN_M0A_OLMO_MLP_SUBSPACE_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "layers":LAYERS,
    "groups_per_layer":GROUPS,
    "baseline":baseline,
    "useful_signal_case_ids":useful_ids,
    "known_baseline_failure_case_ids":known_failures,
    "baseline_useful_mean_margin":baseline_useful_mean,
    "intervention":"ZERO_ONE_CONTIGUOUS_NEAR_EQUAL_GROUP_OF_MLP_DOWN_PROJECTION_INPUT",
    "material_rule":"USEFUL_BASELINE_CORRECT_MEAN_MARGIN_MINUS_ABLATED_USEFUL_MEAN_MARGIN_GE_0_10_OR_ANY_USEFUL_BASELINE_CORRECT_CASE_FLIPS_WRONG",
    "known_failure_rule":"KNOWN_BASELINE_FAILURES_ARE_DIAGNOSTIC_ONLY_AND_CANNOT_MAKE_A_GROUP_MATERIAL",
    "ranked_group_ablation":rows,
    "material_groups":[{"layer":x["layer"],"group":x["group"],"start":x["start"],"end":x["end"]} for x in rows if x["material"]],
    "classification":"MATERIAL_SUBSPACES_LOCALIZED" if any(x["material"] for x in rows) else "DISTRIBUTED_WITHIN_SELECTED_MLPS_AT_8_GROUP_GRANULARITY",
    "heldout_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
