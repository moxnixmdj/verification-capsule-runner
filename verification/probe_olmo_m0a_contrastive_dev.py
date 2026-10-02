import json, math, time, resource
from pathlib import Path
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO="allenai/OLMo-2-0425-1B"
SHA="a1847dff35000b4271fa70afc5db10fd29fedbdf"
CASES=[
("DEV_PRONOUN_SINGULAR_001","The backup process shall verify the checksum. It shall abort on any mismatch."," The backup process shall abort on any mismatch."," The checksum shall abort on any mismatch."),
("DEV_PLURAL_PRONOUN_001","The parser and verifier shall record their versions. They shall reject incompatible schemas."," The parser and verifier shall reject incompatible schemas."," Their versions shall reject incompatible schemas."),
("DEV_FORMER_LATTER_001","The producer writes candidate.json and the verifier writes verdict.json. The former must not overwrite the latter."," The producer must not overwrite verdict.json."," The verifier must not overwrite candidate.json."),
("DEV_ELLIPSIS_TOO_001","The primary node must persist the lease. The replica must, too."," The replica must persist the lease."," The replica must delete the lease."),
("DEV_CONDITIONAL_ANAPHORA_001","If maintenance mode is enabled, the service shall reject writes. In that mode, it may still serve reads."," When maintenance mode is enabled, the service may still serve reads."," When maintenance mode is enabled, maintenance mode may still serve reads."),
("DEV_DEMONSTRATIVE_EVENT_001","The verifier shall recompute the manifest hash. This validation must occur before promotion."," Recomputing the manifest hash must occur before promotion."," Promotion must occur before recomputing the manifest hash."),
("DEV_RESPECTIVELY_001","The producer and verifier shall write candidate.json and verdict.json, respectively."," The producer shall write candidate.json and the verifier shall write verdict.json."," The producer shall write verdict.json and the verifier shall write candidate.json."),
]
AMB=("DEV_AMBIGUOUS_PRONOUN_001","The loader notified the verifier after the parser failed because it was unavailable.",[
" The loader was unavailable."," The verifier was unavailable."," The parser was unavailable."])

path=snapshot_download(REPO,revision=SHA,local_dir="/tmp/olmo",allow_patterns=["*.json","*.txt","*.model","*.safetensors"])
tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"})
model.eval()

def score(source,candidate):
    full=source+candidate
    enc=tok(full,return_tensors="pt",return_offsets_mapping=True,add_special_tokens=True)
    offsets=enc.pop("offset_mapping")[0].tolist()
    with torch.inference_mode():
        logits=model(**enc).logits[0]
    logp=torch.log_softmax(logits,dim=-1)
    ids=enc["input_ids"][0]
    vals=[]
    boundary=len(source)
    for t,(a,b) in enumerate(offsets):
        if t==0: continue
        if a>=boundary and b>a:
            vals.append(float(logp[t-1,ids[t]].item()))
    assert vals,(source,candidate,offsets)
    return sum(vals)/len(vals),len(vals)

rows=[]; wins=0
for cid,src,correct,wrong in CASES:
    cs,cn=score(src,correct); ws,wn=score(src,wrong)
    win=cs>ws; wins+=int(win)
    rows.append({"id":cid,"correct_mean_logprob":cs,"wrong_mean_logprob":ws,"margin":cs-ws,"correct_tokens":cn,"wrong_tokens":wn,"correct_wins":win})
amb_scores=[]
for cand in AMB[2]:
    sc,n=score(AMB[1],cand); amb_scores.append({"candidate":cand,"mean_logprob":sc,"tokens":n})
amb_scores.sort(key=lambda x:x["mean_logprob"],reverse=True)
result={
"schema":"PROJECT_BRAIN_M0A_OLMO_CONTRASTIVE_DEV_RESULT_V1",
"donor":REPO,"resolved_hf_sha":SHA,
"score_rule":"MEAN_LOGPROB_PER_CANDIDATE_TOKEN__CORRECT_GREATER_THAN_WRONG",
"wins":wins,"total":len(CASES),"rows":rows,
"ambiguity_diagnostic":amb_scores,
"ambiguity_rule":"DONOR_PREFERENCE_HAS_ZERO_AUTHORITY_WHEN_BRAIN_IDENTIFIABILITY_GATE_SAYS_AMBIGUOUS",
"peak_rss_kb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
"capability_credit":False,"heldout_used":False,"incremental_spend_usd":0}
print("RESULT_JSON="+json.dumps(result,sort_keys=True))
