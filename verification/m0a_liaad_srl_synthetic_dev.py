import io, json, urllib.request
import torch
from huggingface_hub import model_info, snapshot_download
from transformers import AutoTokenizer, AutoModel

MODEL="liaad/srl-en_mbert-base"
DECODER_SHA="634d145cdca1aa2dfb0cf66143e3a358ac6e56fd"
LINEAR_URL=f"https://raw.githubusercontent.com/asofiaoliveira/srl_bert_pt/{DECODER_SHA}/Models/srl-en_mbert-base/linear_layer.pt"
LABELS_URL=f"https://raw.githubusercontent.com/asofiaoliveira/srl_bert_pt/{DECODER_SHA}/Models/srl-en_mbert-base/Vocabulary/labels.txt"
CASES=[
  {"id":"SRL_ACTIVE_WRITE","words":["The","parser","writes","the","manifest","."],"verb_index":2,"expect":{1:"A0",4:"A1"}},
  {"id":"SRL_ACTIVE_REJECT","words":["The","verifier","rejected","the","candidate","."],"verb_index":2,"expect":{1:"A0",4:"A1"}},
  {"id":"SRL_PASSIVE_WRITE","words":["The","manifest","was","written","by","the","parser","."],"verb_index":3,"expect":{1:"A1",6:"A0"}},
  {"id":"SRL_ACTIVE_MOVE","words":["The","operator","moved","the","file","to","the","archive","."],"verb_index":2,"expect":{1:"A0",4:"A1"}}
]

info=model_info(MODEL)
resolved=info.sha
license_tag=(info.card_data or {}).get("license") if hasattr(info.card_data,"get") else getattr(info.card_data,"license",None)
path=snapshot_download(MODEL,revision=resolved,local_dir="/tmp/liaad_srl",allow_patterns=["*.json","*.txt","*.model","*.safetensors","*.bin"])
tok=AutoTokenizer.from_pretrained(path,local_files_only=True,use_fast=True)
model=AutoModel.from_pretrained(path,local_files_only=True)
model.eval()

with urllib.request.urlopen(LABELS_URL) as f:
    labels=[x.strip() for x in f.read().decode("utf-8").splitlines() if x.strip()]
with urllib.request.urlopen(LINEAR_URL) as f:
    state=torch.load(io.BytesIO(f.read()),map_location="cpu",weights_only=True)
linear=torch.nn.Linear(model.config.hidden_size,len(labels))
linear.load_state_dict(state)
linear.eval()

def role_ok(tag,role):
    return tag in (f"B-{role}",f"I-{role}")

results=[]
for case in CASES:
    enc=tok(case["words"],is_split_into_words=True,return_tensors="pt",add_special_tokens=True)
    word_ids=enc.word_ids(batch_index=0)
    type_ids=torch.zeros_like(enc["input_ids"])
    for i,wid in enumerate(word_ids):
        if wid==case["verb_index"]:
            type_ids[0,i]=1
    with torch.inference_mode():
        out=model(input_ids=enc["input_ids"],attention_mask=enc["attention_mask"],token_type_ids=type_ids,return_dict=True)
        logits=linear(out.last_hidden_state)[0]
    word_tags=[]
    for wi in range(len(case["words"])):
        positions=[i for i,wid in enumerate(word_ids) if wid==wi]
        if not positions:
            word_tags.append(None)
            continue
        word_tags.append(labels[int(logits[positions[0]].argmax())])
    checks={str(i):{"expected":role,"tag":word_tags[i],"pass":role_ok(word_tags[i],role)} for i,role in case["expect"].items()}
    passed=all(x["pass"] for x in checks.values())
    results.append({"id":case["id"],"words":case["words"],"verb_index":case["verb_index"],"word_tags":word_tags,"checks":checks,"pass":passed})

passes=sum(r["pass"] for r in results)
print("RESULT_JSON="+json.dumps({
  "schema":"PROJECT_BRAIN_M0A_LIAAD_SRL_SYNTHETIC_DEV_RESULT_V1",
  "model":MODEL,
  "resolved_hf_sha":resolved,
  "hf_license_tag":license_tag,
  "decoder_repo":"asofiaoliveira/srl_bert_pt",
  "decoder_sha":DECODER_SHA,
  "case_passes":passes,
  "case_total":len(results),
  "signal_present":passes>=3,
  "results":results,
  "heldout_exposed":0,
  "fresh_terminal_evidence_consumed":0,
  "capability_credit":False,
  "incremental_spend_usd":0
},sort_keys=True))
