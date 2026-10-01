#!/usr/bin/env python3
import importlib.util, json, sys, time
from pathlib import Path
from sentence_transformers import CrossEncoder

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("c3router",HERE/"cognitive_tool_router.py")
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
data=json.loads((HERE/"cases.json").read_text())
model_id="cross-encoder/ettin-reranker-150m-v1"
model=CrossEncoder(model_id)

def score(query, descriptions):
    return [float(x) for x in model.predict([(query,d) for d in descriptions])]

rows=[]
for c in data["cases"]:
    routes=[m.ToolRoute(**r) for r in c["routes"]]
    t0=time.perf_counter()
    raw_scores=score(c["query"],[r.description for r in routes])
    raw_ms=(time.perf_counter()-t0)*1000
    raw_pick=routes[max(range(len(routes)),key=lambda i:raw_scores[i])].route_id

    allowed=set(c["allowed_route_ids"]) if c["allowed_route_ids"] is not None else None
    t1=time.perf_counter()
    d=m.select_route(c["query"],routes,score,required_provider=c["required_provider"],allowed_route_ids=allowed)
    filtered_ms=(time.perf_counter()-t1)*1000
    filtered_pick=d.route_id if d.status=="SELECT" else "ESCALATE"

    rows.append({
      "id":c["id"],"gold":c["gold"],
      "raw_pick":raw_pick,"raw_correct":raw_pick==c["gold"],"raw_latency_ms":raw_ms,
      "filtered_pick":filtered_pick,"filtered_correct":filtered_pick==c["gold"],"filtered_latency_ms":filtered_ms,
      "filter_reason":d.reason,"eligible_route_ids":list(d.eligible_route_ids)
    })
n=len(rows)
result={
 "schema":"PROJECT_BRAIN_C3_FILTERED_ETTIN_FRESH_TRANSFER_RESULT_V1",
 "status":"MEASUREMENT_ONLY__ZERO_CAPABILITY_CREDIT",
 "model":model_id,
 "cases":n,
 "raw_hit_at_1":sum(r["raw_correct"] for r in rows)/n,
 "filtered_terminal_accuracy":sum(r["filtered_correct"] for r in rows)/n,
 "raw_wrong":sum(not r["raw_correct"] for r in rows),
 "filtered_wrong":sum(not r["filtered_correct"] for r in rows),
 "safe_escalations":sum(r["filtered_pick"]=="ESCALATE" and r["gold"]=="ESCALATE" for r in rows),
 "mean_raw_latency_ms":sum(r["raw_latency_ms"] for r in rows)/n,
 "mean_filtered_latency_ms":sum(r["filtered_latency_ms"] for r in rows)/n,
 "rows":rows,
 "capability_credit_delta":0
}
(HERE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k] for k in ["cases","raw_hit_at_1","filtered_terminal_accuracy","raw_wrong","filtered_wrong","safe_escalations","mean_raw_latency_ms","mean_filtered_latency_ms"]},indent=2))
