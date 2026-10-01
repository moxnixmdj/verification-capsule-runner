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

spec=importlib.util.spec_from_file_location("c3router", ROUTER)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m
assert spec.loader is not None; spec.loader.exec_module(m)

data=json.loads(CASES.read_text())
skill=json.loads(SKILL.read_text())
model=CrossEncoder(MODEL_ID)

def score(query, descriptions):
    return [float(x) for x in model.predict([(query,d) for d in descriptions])]

rows=[]
for ep in data["episodes"]:
    routes=[m.ToolRoute(**r) for r in ep["routes"]]
    allowed=set(ep["allowed_route_ids"]) if ep.get("allowed_route_ids") else None
    t0=time.perf_counter()
    d=m.select_route(
        ep["query"], routes, score,
        required_provider=ep.get("required_provider"),
        allowed_route_ids=allowed,
    )
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
      "latency_ms":ms,"semantic_choice_required":d.status=="SELECT" and len(d.eligible_route_ids)>1,
      "eligible_route_ids":list(d.eligible_route_ids)
    })

semantic=[r for r in rows if r["semantic_choice_required"]]
ettin_total=sum(r["correct"] for r in rows)/len(rows)
ettin_sem=sum(r["correct"] for r in semantic)/len(semantic)
ettin_latency=sum(r["latency_ms"] for r in rows)/len(rows)
skill_total=float(skill["skillrouter_batched"]["terminal_success_rate"])
skill_sem=float(skill["skillrouter_batched"]["semantic_terminal_success_rate"])
skill_latency=float(skill["skillrouter_batched"]["mean_routing_latency_ms"])
result={
  "schema":"PROJECT_BRAIN_C3_ETTIN_VS_SKILLROUTER_SAME_FROZEN_CASES_001_RESULT_V1",
  "status":"SAME_FROZEN_CASE_HEAD_TO_HEAD__ZERO_CAPABILITY_CREDIT",
  "frozen_cases_commit":"28ab0f0a62e7ad23294945403639d9b6e42736df",
  "ettin_model":MODEL_ID,
  "skillrouter_model":skill["model"],
  "episodes":len(rows),
  "semantic_episodes":len(semantic),
  "ettin_terminal_success_rate":ettin_total,
  "ettin_semantic_success_rate":ettin_sem,
  "ettin_mean_routing_latency_ms":ettin_latency,
  "ettin_failures":[r["id"] for r in rows if not r["correct"]],
  "skillrouter_terminal_success_rate":skill_total,
  "skillrouter_semantic_success_rate":skill_sem,
  "skillrouter_mean_routing_latency_ms":skill_latency,
  "ettin_latency_fraction_vs_skillrouter":ettin_latency/skill_latency,
  "ettin_speedup_vs_skillrouter":skill_latency/ettin_latency if ettin_latency else None,
  "adjudication":(
    "PREFER_ETTIN_FOR_C3_INTERNALIZATION_EVALUATION"
    if ettin_total==skill_total and ettin_sem==skill_sem and ettin_latency < skill_latency
    else "NO_DOMINANCE__KEEP_BOTH_OR_SEARCH_NEXT"
  ),
  "rows":rows,
  "capability_credit_delta":0
}
OUT.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
