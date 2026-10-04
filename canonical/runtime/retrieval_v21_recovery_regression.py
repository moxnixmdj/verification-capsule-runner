#!/usr/bin/env python3
from __future__ import annotations
import json
from canonical.runtime import retrieval_fresh_v4_holdout_v20 as v20
from canonical.runtime import retrieval_query_variant_executor_v21 as qv

SCHEMA="PROJECT_BRAIN_RETRIEVAL_V21_RECOVERY_REGRESSION"

def run(limit:int=20,timeout:float=20.0)->dict:
    events=[]
    for seq,row in enumerate(v20.TASKS,1):
        plan=v20.ep.compile_authorized_plan(
            root=v20.root(),
            query_actions=[v20.query_action(row)],
            sources=[v20.source_row(row)],
        )
        assert plan["status"].startswith("PASS__")
        assert not v20.identity_leaked(plan,v20.v11._norm(row["target"]))
        route_ids=[x.get("strategy_id") for x in plan.get("route_portfolio",{}).get("actions",[])]
        use_multi="MULTI_QUERY_DECOMPOSITION" in route_ids
        trace=qv.execute(row["provider"],row["query"],limit=limit,timeout=timeout,max_variants=12 if use_multi else 1)
        ids=list(trace["candidate_ids"]);seen=set(ids)
        recovery=None
        if row["provider"]=="maven" and any(x in route_ids for x in ("REPOSITORY_MANIFEST_BRIDGE","DEEP_MANIFEST_INSPECTION")):
            extra,recovery=v20.maven_manifest_recovery(row,timeout=timeout)
            for x in extra:
                if x not in seen:seen.add(x);ids.append(x)
        target=v20.v11._norm(row["target"])
        hit=target in set(ids)
        events.append({
            "sequence":seq,"episode_id":row["id"],"provider":row["provider"],
            "query":row["query"],"route_ids":route_ids,
            "candidate_ids":ids,"target_hit":hit,
            "target_rank":ids.index(target)+1 if hit else None,
            "expected_target":target,"variant_trace":trace,"recovery_trace":recovery
        })
    hits=[x for x in events if x["target_hit"]]
    misses=[x for x in events if not x["target_hit"]]
    by={}
    for p in sorted({x["provider"] for x in events}):
        rs=[x for x in events if x["provider"]==p]
        hh=[x for x in rs if x["target_hit"]]
        by[p]={"tasks":len(rs),"hits":len(hh),"recall":len(hh)/len(rs)}
    return {
        "schema":SCHEMA,"status":"COMPLETE","task_count":len(events),
        "hit_count":len(hits),"miss_count":len(misses),"recall":len(hits)/len(events),
        "miss_episode_ids":[x["episode_id"] for x in misses],
        "provider_metrics":by,"events":events,
        "baseline_v20_recall":5/18,
        "open_world_completeness_claim":False,"incremental_spend_usd":0,
        "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
        "execution_authority":False,"promotion_authority":False
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
