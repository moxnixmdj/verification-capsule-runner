import json, os, pathlib, sys
import torch
import stanza

MODEL_DIR="/tmp/stanza_s0e"
PKG="udcoref_xlm-roberta-lora"

result={
    "schema":"PROJECT_BRAIN_S0E_STANZA_COREF_DELTA_INSPECTION_V1",
    "stanza_version":getattr(stanza,"__version__",None),
    "package":PKG,
    "heldout_exposed":0,
    "fresh_terminal_evidence_consumed":0,
    "capability_credit":False,
    "family_credit":False,
    "incremental_spend_usd":0,
    "errors":[],
}

try:
    stanza.download(
        "en",
        processors={"coref":PKG},
        package=None,
        model_dir=MODEL_DIR,
        verbose=False,
    )
except TypeError:
    stanza.download(
        "en",
        processors={"coref":PKG},
        package=None,
        dir=MODEL_DIR,
        verbose=False,
    )

pts=sorted(pathlib.Path(MODEL_DIR).rglob("*.pt"))
result["pt_files"]=[{"path":str(p),"bytes":p.stat().st_size} for p in pts]
if not pts:
    result["errors"].append("NO_PT_CHECKPOINT_FOUND")
    print("RESULT_JSON="+json.dumps(result,sort_keys=True))
    raise SystemExit(1)

# Prefer a coref-named checkpoint.
coref=[p for p in pts if "coref" in str(p).lower() or PKG in p.name.lower()]
ckpt=coref[0] if coref else pts[0]
result["checkpoint_path"]=str(ckpt)
result["checkpoint_bytes"]=ckpt.stat().st_size

state=torch.load(ckpt,map_location="cpu",weights_only=True)
result["top_level_keys"]=sorted(str(k) for k in state.keys())
config=state.get("config",{})
result["config"]={
    k:config.get(k) for k in [
        "bert_model","lora","lora_rank","lora_alpha","lora_target_modules",
        "lora_modules_to_save","bert_finetune","hidden_size","n_hidden_layers",
        "embedding_size","rough_k","full_pairwise"
    ] if isinstance(config,dict) and k in config
}

def count_tensor_tree(obj):
    params=0
    bytes_=0
    tensors=0
    if torch.is_tensor(obj):
        tensors=1
        params=obj.numel()
        bytes_=obj.numel()*obj.element_size()
    elif isinstance(obj,dict):
        for v in obj.values():
            p,b,t=count_tensor_tree(v)
            params+=p; bytes_+=b; tensors+=t
    elif isinstance(obj,(list,tuple)):
        for v in obj:
            p,b,t=count_tensor_tree(v)
            params+=p; bytes_+=b; tensors+=t
    return params,bytes_,tensors

breakdown={}
for k,v in state.items():
    if k in ("config","epochs_trained"):
        continue
    p,b,t=count_tensor_tree(v)
    breakdown[str(k)]={"parameters":p,"tensor_bytes":b,"tensors":t}
result["state_breakdown"]=breakdown
result["total_task_checkpoint_parameters"]=sum(x["parameters"] for x in breakdown.values())
result["total_task_checkpoint_tensor_bytes"]=sum(x["tensor_bytes"] for x in breakdown.values())

lora_keys=[k for k in breakdown if "lora" in k.lower() or "peft" in k.lower() or "bert" in k.lower()]
head_keys=[k for k in breakdown if k not in lora_keys]
result["lora_or_bert_keys"]=lora_keys
result["non_bert_head_keys"]=head_keys
result["lora_or_bert_parameters"]=sum(breakdown[k]["parameters"] for k in lora_keys)
result["non_bert_head_parameters"]=sum(breakdown[k]["parameters"] for k in head_keys)

# Fail closed if checkpoint unexpectedly embeds a full transformer-scale state.
result["appears_delta_sized"] = result["total_task_checkpoint_parameters"] < 100_000_000
result["status"]="PASS" if result["appears_delta_sized"] and not result["errors"] else "FAIL_CLOSED"

print("RESULT_JSON="+json.dumps(result,sort_keys=True))
