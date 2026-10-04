#!/usr/bin/env python3
from __future__ import annotations
import itertools,time
from typing import Any,Sequence
from canonical.runtime import retrieval_live_provider_arena_v11 as v11
SCHEMA="PROJECT_BRAIN_RETRIEVAL_QUERY_VARIANT_EXECUTOR_V21"
STOP={"rust","java","kotlin","ruby","php","python","javascript","typescript","node","node.js",".net","dotnet","library","framework"}

def canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def variants(query:str,provider:str,max_variants:int=12)->list[str]:
    base=" ".join(x for x in canon(query).split() if not x.startswith("in:"))
    toks=[x.strip(" ,;:()[]{}") for x in base.split()]
    toks=[x for x in toks if x]
    useful=[x for x in toks if x.casefold() not in STOP]
    out=[];seen=set()
    def add(parts):
        q=canon(" ".join(parts) if not isinstance(parts,str) else parts)
        if not q or q.casefold() in seen:return
        seen.add(q.casefold())
        if provider=="github":q=q+" in:name,description,readme"
        out.append(q)
    add(base)
    if useful!=toks:add(useful)
    for n in (2,3,4):
        for i in range(max(0,len(useful)-n+1)):
            add(useful[i:i+n])
            if len(out)>=max_variants:return out
    for a,b in itertools.combinations(useful[:6],2):
        add([a,b])
        if len(out)>=max_variants:return out
    return out[:max_variants]

def execute(provider:str,query:str,*,limit:int=20,timeout:float=20.0,max_variants:int=12)->dict[str,Any]:
    fn=v11.PROVIDERS[provider]
    ids=[];seen=set();traces=[]
    qs=variants(query,provider,max_variants)
    for q in qs:
        start=time.perf_counter()
        try:
            raw=fn(q,limit=limit,timeout=timeout);status="SUCCESS";err=None
        except Exception as exc:
            raw=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:240]}"
        rows=[v11._norm(x) for x in raw if v11._norm(x)]
        for x in rows:
            if x not in seen:seen.add(x);ids.append(x)
        traces.append({"query":q,"status":status,"count":len(rows),"latency":max(0.0,time.perf_counter()-start),"error":err})
    return {"schema":SCHEMA,"status":"COMPLETE","candidate_ids":ids,"queries":qs,"traces":traces,
            "open_world_completeness_claim":False,"incremental_spend_usd":0,
            "execution_authority":False,"promotion_authority":False}
