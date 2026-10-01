#!/usr/bin/env python3
import json, time, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/"cases.json").read_text())
model_id="MoritzLaurer/deberta-v3-base-zeroshot-v1"
tok=AutoTokenizer.from_pretrained(model_id)
model=AutoModelForSequenceClassification.from_pretrained(model_id)
model.eval()

id2label={int(k):v for k,v in model.config.id2label.items()} if isinstance(model.config.id2label,dict) else model.config.id2label
def entailment_index():
    for i,label in id2label.items():
        l=str(label).lower()
        if ("entail" in l and "not" not in l) or l in {"true","label_1"}:
            return int(i)
    if len(id2label)==2:
        return 1
    raise RuntimeError(f"Cannot identify entailment label from {id2label}")
ent_i=entailment_index()
rows=[]
for case in data["cases"]:
    inputs=tok(case["evidence"], case["claim"], return_tensors="pt", truncation=True, max_length=1024)
    t0=time.perf_counter()
    with torch.no_grad():
        logits=model(**inputs).logits[0]
        probs=torch.softmax(logits,dim=-1)
    ms=(time.perf_counter()-t0)*1000
    p=float(probs[ent_i])
    pred=p>=0.5
    rows.append({"id":case["id"],"gold":case["gold"],"predicted":pred,"correct":pred==case["gold"],"entailment_probability":p,"latency_ms":ms})
n=len(rows)
result={
 "schema":"PROJECT_BRAIN_C9_SEMANTIC_SUPPORT_NLI_PROBE_RESULT_V1",
 "status":"MEASUREMENT_ONLY__ZERO_CAPABILITY_CREDIT",
 "model":model_id,
 "id2label":id2label,
 "entailment_index":ent_i,
 "cases":n,
 "accuracy":sum(r["correct"] for r in rows)/n,
 "mean_latency_ms":sum(r["latency_ms"] for r in rows)/n,
 "wrong_cases":[r for r in rows if not r["correct"]],
 "rows":rows,
 "scope_warning":"THIS_MEASURES_SEMANTIC_SUPPORT_RELATION_ONLY__NOT_COMPLETE_EVIDENCE_SUFFICIENCY_OR_PROMOTION_AUTHORITY",
 "capability_credit_delta":0
}
(HERE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k] for k in ["cases","accuracy","mean_latency_ms","id2label","entailment_index"]},indent=2))
