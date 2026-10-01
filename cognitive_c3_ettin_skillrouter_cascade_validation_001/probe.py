#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, sys, time
from pathlib import Path
from sentence_transformers import CrossEncoder

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/"cognitive_c3_skillrouter_fresh_001"/"cases.json"
ROUTER=ROOT/"cognitive_c3_skillrouter_fresh_001"/"cognitive_tool_router.py"
SKILL=ROOT/"cognitive_c3_skillrouter_fresh_001"/"result.json"
OUT=Path(__file__).resolve().parent/"result.json"
MODEL_ID="cross-encoder/ettin-reranker-150m-v1"
THRESHOLD=0.9530563354492188

spec=importlib.util.spec_from_file_location("c3router", ROUTER)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m
assert spec.loader is not None; spec.loader.exec_module(m)

data=json.loads(CASES.read_text())
skill=json.loads(SKILL.read_text())
skill_by_id={r["id"]:r for r in skill["skillrouter_batched_rows"]}
model=CrossEncoder(MODEL_ID)

def score(query, descriptions):
    return [float(x) for x in model.predict([(query,d) for d in descriptions])]

rows=[]
for ep in data["episodes"]:
    routes=[m.ToolRoute(**r) for r in ep["routes"]]
    allowed=set(ep["allowed_route_ids"]) if ep.get("allowed_route_ids") else None
    eligible=m.eligible_routes(routes,required_provider=ep.get("required_provider"),allowed_route_ids=allowed)
    t0=time.perf_counter()
    scores={}
    margin=None
    if not eligible:
        pick="ESCALATE"; ettin_correct=ep.get("expected_status")=="ESCALATE"; semantic=False
    elif len(eligible)==1:
        pick=eligible[0].route_id
        ettin_correct=ep.get("expected_status","SELECT")=="SELECT" and pick==ep.get("expected_route")
        semantic=False
        scores={pick:None}
    else:
        vals=score(ep["query"],[r.description for r in eligible])
        scores={r.route_id:float(v) for r,v in zip(eligible,vals)}
        order=sorted(range(len(vals)),key=lambda i:vals[i],reverse=True)
        pick=eligible[order[0]].route_id
        margin=float(vals[order[0]]-vals[order[1]])
        ettin_correct=pick==ep.get("expected_route")
        semantic=True
    ms=(time.perf_counter()-t0)*1000
    fallback=bool(semantic and margin is not None and margin<=THRESHOLD)
    skill_correct=bool(skill_by_id[ep["id"]]["terminal_success"])
    composed_correct=skill_correct if fallback else bool(ettin_correct)
    rows.append({
      "id":ep["id"],"ettin_pick":pick,"ettin_correct":bool(ettin_correct),
      "ettin_latency_ms":ms,"semantic":semantic,"scores":scores,
      "top1_top2_margin":margin,"fallback_to_skillrouter":fallback,
      "skillrouter_correct":skill_correct,"composed_correct":composed_correct
    })

semantic=[r for r in rows if r["semantic"]]
fallbacks=[r for r in semantic if r["fallback_to_skillrouter"]]
ettin_mean=sum(r["ettin_latency_ms"] for r in rows)/len(rows)
skill_mean=float(skill["skillrouter_batched"]["mean_routing_latency_ms"])
effective_mean=ettin_mean + len(fallbacks)/len(rows)*skill_mean
result={
  "schema":"PROJECT_BRAIN_C3_ETTIN_SKILLROUTER_CASCADE_VALIDATION_001_RESULT_V1",
  "status":"VALIDATE_SPENT20_DERIVED_THRESHOLD_ON_NEWER_FROZEN_SET__ZERO_CAPABILITY_CREDIT",
  "threshold_source":"cognitive_c3_ettin_on_skillrouter_spent20_001/result.json",
  "fixed_margin_threshold":THRESHOLD,
  "frozen_cases_commit":"28ab0f0a62e7ad23294945403639d9b6e42736df",
  "episodes":len(rows),
  "semantic_episodes":len(semantic),
  "ettin_success_rate":sum(r["ettin_correct"] for r in rows)/len(rows),
  "skillrouter_success_rate":sum(r["skillrouter_correct"] for r in rows)/len(rows),
  "cascade_success_rate":sum(r["composed_correct"] for r in rows)/len(rows),
  "semantic_cascade_success_rate":sum(r["composed_correct"] for r in semantic)/len(semantic),
  "fallbacks":len(fallbacks),
  "fallback_fraction_semantic":len(fallbacks)/len(semantic),
  "fallback_ids":[r["id"] for r in fallbacks],
  "uncaught_ettin_failures":[r["id"] for r in semantic if not r["ettin_correct"] and not r["fallback_to_skillrouter"]],
  "unnecessary_fallbacks":[r["id"] for r in semantic if r["ettin_correct"] and r["fallback_to_skillrouter"]],
  "ettin_mean_routing_latency_ms":ettin_mean,
  "skillrouter_mean_routing_latency_ms":skill_mean,
  "estimated_cascade_mean_routing_latency_ms":effective_mean,
  "estimated_speedup_vs_always_skillrouter":skill_mean/effective_mean if effective_mean else None,
  "rows":rows,
  "capability_credit_delta":0
}
OUT.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
