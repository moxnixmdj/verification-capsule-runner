import json, os, re
import stanza

MODEL_DIR="/tmp/stanza_s0e_lora"
CASES=[
  {"id":"DEV_MANIFEST_IT","text":"The manifest was created by the builder. It contains three files.","pairs":[["manifest","it"]]},
  {"id":"DEV_ALICE_BOB","text":"Alice gave Bob the report after the meeting. She emailed him a copy.","pairs":[["alice","she"],["bob","him"]]},
  {"id":"DEV_CONJUNCTION","text":"The parser and verifier checked the package. They approved it.","pairs":[["parser and verifier","they"],["package","it"]]},
  {"id":"DEV_LONG_RANGE","text":"The service starts in maintenance mode. The database remains read-only. Requests are queued. Operators inspect the logs. It resumes normal operation after approval.","pairs":[["service","it"]]},
  {"id":"DEV_COMMONSENSE_LARGE","text":"The trophy does not fit in the suitcase because it is too large.","pairs":[["trophy","it"]]},
]

stanza.download("en", processors="tokenize,coref", model_dir=MODEL_DIR, verbose=False)
pipe=stanza.Pipeline(
    "en",
    processors="tokenize,coref",
    model_dir=MODEL_DIR,
    download_method=None,
    use_gpu=False,
    coref_use_zeros=False,
    verbose=False,
)
coref_model=pipe.processors["coref"]._model
bert=coref_model.bert

def norm(s):
    return re.sub(r"[^a-z0-9 ]+","",s.lower()).strip()

def mention_text(doc,m):
    if not isinstance(m.start_word,int) or not isinstance(m.end_word,int):
        return "_ZERO_"
    return " ".join(w.text for w in doc.sentences[m.sentence].words[m.start_word:m.end_word])

def evaluate_case(case):
    doc=pipe(case["text"])
    chains=[]
    for ch in doc.coref:
        texts=[mention_text(doc,m) for m in ch.mentions]
        chains.append(texts)
    pair_rows=[]
    for a,b in case["pairs"]:
        aa=norm(a); bb=norm(b)
        ok=False
        hit=None
        for texts in chains:
            ns=[norm(x) for x in texts]
            has_a=any(aa in x or x in aa for x in ns if x)
            has_b=any(bb==x or bb in x.split() for x in ns if x)
            if has_a and has_b:
                ok=True; hit=texts; break
        pair_rows.append({"a":a,"b":b,"pass":ok,"chain":hit})
    return {"id":case["id"],"pairs":pair_rows,"chains":chains,"pass":all(x["pass"] for x in pair_rows)}

full=[evaluate_case(c) for c in CASES]

if not hasattr(bert,"disable_adapter"):
    raise RuntimeError("PEFT wrapper missing disable_adapter context manager")
with bert.disable_adapter():
    no_lora=[evaluate_case(c) for c in CASES]

def counts(rows):
    pair_total=sum(len(x["pairs"]) for x in rows)
    pair_pass=sum(sum(1 for p in x["pairs"] if p["pass"]) for x in rows)
    case_pass=sum(1 for x in rows if x["pass"])
    return {"pair_pass":pair_pass,"pair_total":pair_total,"case_pass":case_pass,"case_total":len(rows)}

fc=counts(full); nc=counts(no_lora)
pair_drop=fc["pair_pass"]-nc["pair_pass"]
case_drop=fc["case_pass"]-nc["case_pass"]

out={
 "schema":"PROJECT_BRAIN_S0E_STANZA_LORA_ABLATION_DEV_V1",
 "stanza_version":stanza.__version__,
 "model_package":"udcoref_xlm-roberta-lora",
 "intervention":"DISABLE_PEFT_LORA_ADAPTER_ONLY__SAME_XLM_ROBERTA_BACKBONE_AND_COREF_HEADS",
 "full":fc,
 "no_lora":nc,
 "pair_pass_drop":pair_drop,
 "case_pass_drop":case_drop,
 "lora_material": pair_drop>0 or case_drop>0,
 "full_rows":full,
 "no_lora_rows":no_lora,
 "heldout_exposed":0,
 "fresh_terminal_evidence_consumed":0,
 "capability_credit":False,
 "family_credit":False,
 "incremental_spend_usd":0
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
