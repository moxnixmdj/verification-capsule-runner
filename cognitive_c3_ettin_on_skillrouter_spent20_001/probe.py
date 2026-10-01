#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, sys, time
from pathlib import Path
from sentence_transformers import CrossEncoder

ROOT=Path(__file__).resolve().parents[1]
EPISODES=ROOT/"cognitive_c3_skillrouter_batched_spent"/"episodes.json"
ROUTER=ROOT/"cognitive_c3_skillrouter_batched_spent"/"cognitive_tool_router.py"
SKILL=ROOT/"cognitive_c3_skillrouter_batched_spent"/"result.json"
OUT=Path(__file__).resolve().parent/"result.json"
MODEL_ID="cross-encoder/ettin-reranker-150m-v1"

spec=importlib.util.spec_from_file_location("c3router", ROUTER)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m
assert spec.loader is not None; spec.loader.exec_module(m)

data=json.loads(EPISODES.read_text())
skill=json.loads(SKILL.read_text())
model=CrossEncoder(MODEL_ID)

def score(query, descriptions):
    return [float(x) for x in model.predict([(query,d) for d in descriptions])]

rows=[]
for ep in data["episodes"]:
    routes=[m.ToolRoute(**r) for r in ep["routes"]]
    allowed=set(ep["allowed_route_ids"]) if ep.get("allowed_route_ids") else None

    eligible=m.eligible_routes(routes,required_provider=ep.get("required_provider"),allowed_route_ids=allowed)
    t0=time.perf_counter()
    if len(eligible)==0:
        d=m.RouteDecision(status="ESCALATE",route_id=None,reason="NO_DETERMINISTICALLY_ADMISSIBLE_ROUTE",score=None,eligible_route_ids=())
        route_scores={}
        margin=None
    elif len(eligible)==1:
        d=m.RouteDecision(status="SELECT",route_id=eligible[0].route_id,reason="SINGLE_DETERMINISTICALLY_ADMISSIBLE_ROUTE",score=None,eligible_route_ids=(eligible[0].route_id,))
        route_scores={eligible[0].route_id:None}
        margin=None
    else:
        vals=score(ep["query"],[r.description for r in eligible])
        route_scores={r.route_id:float(v) for r,v in zip(eligible,vals)}
        order=sorted(range(len(vals)),key=lambda i:vals[i],reverse=True)
        top=order[0]
        margin=float(vals[order[0]]-vals[order[1]]) if len(order)>1 else None
        d=m.RouteDecision(status="SELECT",route_id=eligible[top].route_id,reason="SEMANTIC_RERANK_AMONG_DETERMINISTICALLY_ADMISSIBLE_ROUTES",score=float(vals[top]),eligible_route_ids=tuple(r.route_id for r in eligible))
    ms=(time.perf_counter()-t0)*1000

    expected_status=ep.get("expected_status","SELECT")
    if d.status=="ESCALATE":
        correct=(expected_status=="ESCALATE")
        pick="ESCALATE"
    else:
        correct=(expected_status=="SELECT" and d.route_id==ep.get("expected_route"))
        pick=d.route_id
    rows.append({
      "id":ep["id"],"pick":pick,"correct":bool(correct),
      "latency_ms":ms,"semantic_choice_required":len(eligible)>1,
      "eligible_route_ids":[r.route_id for r in eligible],
      "scores":route_scores,"top1_top2_margin":margin
    })

semantic=[r for r in rows if r["semantic_choice_required"]]
result={
  "schema":"PROJECT_BRAIN_C3_ETTIN_ON_SKILLROUTER_SPENT20_001_RESULT_V1",
  "status":"SPENT_CROSS_VALIDATION_MEASUREMENT__ZERO_CAPABILITY_CREDIT",
  "ettin_model":MODEL_ID,
  "episodes":len(rows),
  "semantic_episodes":len(semantic),
  "ettin_terminal_success_rate":sum(r["correct"] for r in rows)/len(rows),
  "ettin_semantic_success_rate":sum(r["correct"] for r in semantic)/len(semantic),
  "ettin_mean_routing_latency_ms":sum(r["latency_ms"] for r in rows)/len(rows),
  "ettin_failures":[r["id"] for r in rows if not r["correct"]],
  "skillrouter_terminal_success_rate":skill["skillrouter_batched"]["terminal_success_rate"],
  "skillrouter_semantic_success_rate":skill["skillrouter_batched"]["semantic_terminal_success_rate"],
  "skillrouter_mean_routing_latency_ms":skill["skillrouter_batched"]["mean_routing_latency_ms"],
  "rows":rows,
  "capability_credit_delta":0
}
OUT.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
