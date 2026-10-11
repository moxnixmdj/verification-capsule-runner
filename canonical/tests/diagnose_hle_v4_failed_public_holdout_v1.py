#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.parse, urllib.request
from canonical.runtime import hle_native_open_domain_research_v4 as v4

DATASET="ai-safety-institute/trivia_qa_verified"
CONFIG="default"
SPLIT="validation"
OFFSET=25
LENGTH=25

def fetch_rows():
    url="https://datasets-server.huggingface.co/rows?"+urllib.parse.urlencode({
        "dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":LENGTH,
    })
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-HLE-V4-Diagnostic/1.0"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        payload=json.loads(resp.read().decode("utf-8"))
    return payload["rows"]

def main():
    out=[]
    for item in fetch_rows():
        idx=int(item["row_idx"])
        row=item["row"]
        q=str(row["question"])
        gold=str(row["answer"])
        kind=v4._kind(v4._clean_question(q))
        queries=v4._queries(v4._clean_question(q),kind)
        searches=[]
        for query in queries:
            try:
                hits=v4.wikipedia_search(query,limit=5)
                searches.append({
                    "query":query,
                    "titles":[x.get("title") for x in hits],
                    "snippets":[x.get("snippet") for x in hits],
                })
            except Exception as exc:
                searches.append({"query":query,"error":type(exc).__name__})
        result=v4.propose(task_id=f"triviaqa_validation_row_{idx}",question=q,has_nonempty_image_payload=False)
        out.append({
            "row_idx":idx,
            "question":q,
            "gold":gold,
            "kind":kind,
            "queries":queries,
            "searches":searches,
            "status":result.get("status"),
            "candidate":result.get("candidate_answer"),
            "support_score":result.get("support_score"),
            "top_margin":result.get("top_margin"),
            "reason_classes":result.get("evidence_reason_classes"),
            "retrieved_page_count":result.get("retrieved_page_count"),
        })
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
