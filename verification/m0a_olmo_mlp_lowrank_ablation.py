import json, statistics
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE=json.loads(Path("verification/m0a_olmo_contrastive_dev.json").read_text())
REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"
LAYERS=[1,11]
RANKS=[1,2,4,6]

def tokenize_pair(tok,source,candidate):
    prompt=source+"\nResolution:"
    p=tok(prompt,add_special_tokens=False)["input_ids"]
    c=tok(candidate,add_special_tokens=False)["input_ids"]
    ids=torch.tensor([p+c],dtype=torch.long)
    predictor_positions=list(range(len(p)-1,len(p)+len(c)-1))
    return ids,p,c,predictor_positions

def mean_logprob(model,tok,source,candidate):
    ids,p,c,_=tokenize_pair(tok,source,candidate)
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

def down_proj(layer):
    for name in ("down_proj","ff_out","output_proj"):
        m=getattr(layer.mlp,name,None)
        if m is not None:
            return m,name
    raise RuntimeError("no supported down projection")

def candidate_activation_mean(model,tok,layer_id,source,candidate):
    module,name=down_proj(model.model.layers[layer_id])
    holder={}
    def capture(_m,args):
        x=args[0]
        holder["x"]=x.detach().float().cpu()
    h=module.register_forward_pre_hook(capture)
    try:
        ids,_,_,positions=tokenize_pair(tok,source,candidate)
        with torch.inference_mode():
            model(input_ids=ids,use_cache=False)
    finally:
        h.remove()
    x=holder["x"][0]
    return x[positions].mean(dim=0),name

def make_ablation_hook(basis):
    # basis rows orthonormal, shape [k,width], cpu float32
    def hook(_m,args):
        x=args[0]
        b=basis.to(device=x.device,dtype=torch.float32)
        xf=x.float()
        coeff=torch.matmul(xf,b.T)
        proj=torch.matmul(coeff,b)
        y=(xf-proj).to(dtype=x.dtype)
        return (y,)+tuple(args[1:])
    return hook

path=snapshot_download(
    repo_id=REPO,revision=REV,local_dir="/tmp/olmo2_1b_mlp_lowrank",
    allow_patterns=["*.json","*.txt","*.model","*.safetensors"],
)
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()
baseline=evaluate(model,tok)
base_by={x["id"]:x for x in baseline["rows"]}
useful_ids=[x["id"] for x in baseline["rows"] if x["correct_preferred"]]
useful_mean=statistics.mean(base_by[i]["margin"] for i in useful_ids)

results=[]
for layer_id in LAYERS:
    diffs=[]
    attr=None
    for case in PROBE["cases"]:
        if case["id"] not in useful_ids:
            continue
        ca,attr=candidate_activation_mean(model,tok,layer_id,case["source"],case["correct"])
        wa,_=candidate_activation_mean(model,tok,layer_id,case["source"],case["wrong"])
        diffs.append(ca-wa)
    mat=torch.stack(diffs,dim=0)
    centered=mat-mat.mean(dim=0,keepdim=True)
    U,S,Vh=torch.linalg.svd(centered,full_matrices=False)
    max_rank=int((S>1e-8).sum().item())
    module,_=down_proj(model.model.layers[layer_id])
    for requested_rank in RANKS:
        k=min(requested_rank,max_rank)
        if k<1:
            continue
        basis=Vh[:k].contiguous()
        h=module.register_forward_pre_hook(make_ablation_hook(basis))
        try:
            ab=evaluate(model,tok)
        finally:
            h.remove()
        ab_by={x["id"]:x for x in ab["rows"]}
        useful_ab_mean=statistics.mean(ab_by[i]["margin"] for i in useful_ids)
        flips=[i for i in useful_ids if not ab_by[i]["correct_preferred"]]
        loss=useful_mean-useful_ab_mean
        results.append({
            "layer":layer_id,
            "down_projection_attr":attr,
            "requested_rank":requested_rank,
            "effective_rank":k,
            "available_centered_rank":max_rank,
            "singular_values":[float(x) for x in S[:k]],
            "baseline_correct_subset_mean_margin":useful_mean,
            "ablated_baseline_correct_subset_mean_margin":useful_ab_mean,
            "baseline_correct_subset_margin_loss":loss,
            "baseline_correct_to_wrong_flips":flips,
            "ablated_accuracy":ab["accuracy"],
            "ablated_correct_count":ab["correct_count"],
            "material":loss>=0.10 or bool(flips),
            "per_case_margin_delta":{i:base_by[i]["margin"]-ab_by[i]["margin"] for i in useful_ids},
        })

# Deduplicate cases where requested ranks collapse to same effective rank.
unique={}
for row in results:
    key=(row["layer"],row["effective_rank"])
    if key not in unique:
        unique[key]=row
results=list(unique.values())
results.sort(key=lambda x:(-x["baseline_correct_subset_margin_loss"],x["layer"],x["effective_rank"]))
material=[x for x in results if x["material"]]
smallest={}
for x in sorted(material,key=lambda x:(x["effective_rank"],x["layer"])):
    smallest.setdefault(x["layer"],x)
out={
    "schema":"PROJECT_BRAIN_M0A_OLMO_MLP_LOWRANK_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "layers":LAYERS,
    "baseline":baseline,
    "useful_case_ids":useful_ids,
    "baseline_correct_subset_mean_margin":useful_mean,
    "basis":"CENTERED_SVD_OF_PER_CASE_CORRECT_MINUS_WRONG_MEAN_DOWN_PROJECTION_INPUT_ACTIVATIONS",
    "intervention":"REMOVE_PROJECTION_ONTO_TOP_K_RIGHT_SINGULAR_VECTORS_AT_SELECTED_MLP_DOWN_PROJECTION_INPUT",
    "material_rule":"USEFUL_BASELINE_CORRECT_SUBSET_MEAN_MARGIN_LOSS_GE_0_10_OR_ANY_USEFUL_BASELINE_CORRECT_CASE_FLIPS_WRONG",
    "ranked_ablations":results,
    "material_subspaces":[
        {"layer":x["layer"],"rank":x["effective_rank"],"margin_loss":x["baseline_correct_subset_margin_loss"],"flips":x["baseline_correct_to_wrong_flips"]}
        for x in material
    ],
    "smallest_material_rank_by_layer":{str(k):{"rank":v["effective_rank"],"margin_loss":v["baseline_correct_subset_margin_loss"],"flips":v["baseline_correct_to_wrong_flips"]} for k,v in smallest.items()},
    "classification":"LOW_RANK_CAUSAL_SUBSPACE_FOUND" if material else "NO_MATERIAL_LOW_RANK_LINEAR_SUBSPACE_FOUND_ON_FROZEN_DEV",
    "known_failure":"DEV_FORMER_LATTER_001_EXCLUDED_FROM_BASIS_AND_MATERIALITY_BECAUSE_BASELINE_WRONG",
    "heldout_exposed":0,
    "fresh_terminal_evidence_consumed":0,
    "capability_credit":False,
    "family_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
