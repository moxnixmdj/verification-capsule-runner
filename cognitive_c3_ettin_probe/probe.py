#!/usr/bin/env python3
import json, re, time
from pathlib import Path
from sentence_transformers import CrossEncoder

HERE = Path(__file__).resolve().parent
cases = json.loads((HERE / "cases.json").read_text())
model_id = "cross-encoder/ettin-reranker-150m-v1"

def toks(s):
    return set(re.findall(r"[a-z0-9_]+", s.lower()))

def lexical_score(q, text):
    qv=toks(q); tv=toks(text)
    return len(qv & tv) / max(1, len(qv | tv))

model = CrossEncoder(model_id)
rows=[]
for case in cases["cases"]:
    pairs=[(case["query"], c["text"]) for c in case["candidates"]]
    t0=time.perf_counter()
    scores=[float(x) for x in model.predict(pairs)]
    model_ms=(time.perf_counter()-t0)*1000
    best_i=max(range(len(scores)), key=lambda i:scores[i])
    model_pick=case["candidates"][best_i]["id"]
    lex=[lexical_score(case["query"], c["text"]) for c in case["candidates"]]
    lex_i=max(range(len(lex)), key=lambda i:lex[i])
    lex_pick=case["candidates"][lex_i]["id"]
    rows.append({
      "id":case["id"], "gold":case["gold"],
      "model_pick":model_pick, "model_correct":model_pick==case["gold"],
      "model_scores":{c["id"]:scores[i] for i,c in enumerate(case["candidates"])},
      "model_latency_ms":model_ms,
      "lexical_pick":lex_pick, "lexical_correct":lex_pick==case["gold"],
      "lexical_scores":{c["id"]:lex[i] for i,c in enumerate(case["candidates"])}
    })
n=len(rows)
result={
 "schema":"PROJECT_BRAIN_C3_TOOL_ROUTE_RERANKER_PROBE_RESULT_V1",
 "status":"MEASUREMENT_ONLY__ZERO_CAPABILITY_CREDIT",
 "model":model_id,
 "cases":n,
 "model_hit_at_1":sum(r["model_correct"] for r in rows)/n,
 "lexical_hit_at_1":sum(r["lexical_correct"] for r in rows)/n,
 "mean_model_latency_ms":sum(r["model_latency_ms"] for r in rows)/n,
 "rows":rows,
 "capability_credit_delta":0
}
(HERE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k] for k in ["cases","model_hit_at_1","lexical_hit_at_1","mean_model_latency_ms"]},indent=2))
