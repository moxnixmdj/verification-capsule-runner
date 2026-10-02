import json, statistics, types
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO="allenai/OLMo-2-0425-1B"
REV="a1847dff35000b4271fa70afc5db10fd29fedbdf"
CASES=[
("DEV_PRONOUN_SINGULAR_001","The backup process shall verify the checksum. It shall abort on any mismatch."," The backup process shall abort on any mismatch."," The checksum shall abort on any mismatch."),
("DEV_PLURAL_PRONOUN_001","The parser and verifier shall record their versions. They shall reject incompatible schemas."," The parser and verifier shall reject incompatible schemas."," Their versions shall reject incompatible schemas."),
("DEV_FORMER_LATTER_001","The producer writes candidate.json and the verifier writes verdict.json. The former must not overwrite the latter."," The producer must not overwrite verdict.json."," The verifier must not overwrite candidate.json."),
("DEV_ELLIPSIS_TOO_001","The primary node must persist the lease. The replica must, too."," The replica must persist the lease."," The replica must delete the lease."),
("DEV_CONDITIONAL_ANAPHORA_001","If maintenance mode is enabled, the service shall reject writes. In that mode, it may still serve reads."," When maintenance mode is enabled, the service may still serve reads."," When maintenance mode is enabled, maintenance mode may still serve reads."),
("DEV_DEMONSTRATIVE_EVENT_001","The verifier shall recompute the manifest hash. This validation must occur before promotion."," Recomputing the manifest hash must occur before promotion."," Promotion must occur before recomputing the manifest hash."),
("DEV_RESPECTIVELY_001","The producer and verifier shall write candidate.json and verdict.json, respectively."," The producer shall write candidate.json and the verifier shall write verdict.json."," The producer shall write verdict.json and the verifier shall write candidate.json."),
]

path=snapshot_download(REPO,revision=REV,local_dir="/tmp/olmo2_1b_m0a_layer",allow_patterns=["*.json","*.txt","*.model","*.safetensors"])
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"})
model.eval()

def score(source,candidate):
    prompt=source+"\nResolution:"
    p=tok(prompt,add_special_tokens=False)["input_ids"]
    c=tok(candidate,add_special_tokens=False)["input_ids"]
    ids=torch.tensor([p+c],dtype=torch.long)
    with torch.inference_mode():
        logits=model(input_ids=ids,use_cache=False).logits[0]
        lp=torch.log_softmax(logits,dim=-1)
    vals=[float(lp[j-1,token_id]) for j,token_id in enumerate(c,start=len(p))]
    return sum(vals)/len(vals)

def margins():
    out={}
    for cid,source,correct,wrong in CASES:
        out[cid]=score(source,correct)-score(source,wrong)
    return out

baseline=margins()
baseline_mean=statistics.mean(baseline.values())
layers=model.model.layers
rows=[]
for i,layer in enumerate(layers):
    original=layer.forward
    def identity_forward(self,hidden_states,*args,**kwargs):
        return hidden_states
    layer.forward=types.MethodType(identity_forward,layer)
    try:
        current=margins()
    finally:
        layer.forward=original
    mean_margin=statistics.mean(current.values())
    loss=baseline_mean-mean_margin
    flips=sorted(cid for cid in baseline if baseline[cid]>0 and current[cid]<=0)
    material=(loss>=0.10 or bool(flips))
    rows.append({
        "layer":i,
        "ablated_mean_margin":mean_margin,
        "baseline_minus_ablated_mean_margin":loss,
        "baseline_correct_flips_wrong":flips,
        "material":material,
        "per_case_margin_delta":{cid:baseline[cid]-current[cid] for cid in baseline},
    })

ranked=sorted(rows,key=lambda x:(-x["baseline_minus_ablated_mean_margin"],x["layer"]))
material=[r["layer"] for r in ranked if r["material"]]
result={
 "schema":"PROJECT_BRAIN_M0A_OLMO_LAYER_CAUSAL_LOCALIZATION_RESULT_V1",
 "donor":REPO,
 "resolved_hf_sha":REV,
 "intervention":"ONE_DECODER_LAYER_FORWARD_REPLACED_BY_IDENTITY_HIDDEN_STATE_PASS_THROUGH",
 "layer_count":len(layers),
 "baseline_correct_preference_count":sum(1 for v in baseline.values() if v>0),
 "baseline_mean_margin":baseline_mean,
 "baseline_margins":baseline,
 "material_rule":"BASELINE_MEAN_MARGIN_MINUS_ABLATED_MEAN_MARGIN_GE_0_10_OR_ANY_BASELINE_CORRECT_CASE_FLIPS_WRONG",
 "material_layers":material,
 "classification":"MATERIAL_LAYERS_LOCALIZED" if material else "DISTRIBUTED_AT_LAYER_GRANULARITY",
 "rows":rows,
 "heldout_exposed":0,
 "capability_credit":False,
 "incremental_spend_usd":0
}
print("RESULT_JSON="+json.dumps(result,sort_keys=True))
