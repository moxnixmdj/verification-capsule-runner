#!/usr/bin/env python3
import json, urllib.error, urllib.parse, urllib.request
from canonical.runtime import hle_native_open_domain_research_v5 as m

URL="https://datasets-server.huggingface.co/rows?"+urllib.parse.urlencode({
 "dataset":"ai-safety-institute/trivia_qa_verified","config":"default","split":"validation","offset":25,"length":10})
with urllib.request.urlopen(urllib.request.Request(URL,headers={"User-Agent":"ProjectBrain-TransportProbeV2/1.0"}),timeout=30) as r:
 rows=json.loads(r.read().decode())["rows"]

def err(exc):
    out={"error_class":type(exc).__name__}
    if isinstance(exc,urllib.error.HTTPError):
        out["http_code"]=int(exc.code)
        out["retry_after"]=exc.headers.get("Retry-After") if exc.headers else None
    if isinstance(exc,OSError):
        out["errno"]=getattr(exc,"errno",None)
    out["error"]=str(exc)[:300]
    return out

summary={"bing":{"ok":0,"failed":0,"results":0},"wikipedia":{"ok":0,"failed":0,"results":0},"rows":10}
for item in rows:
    row=item["row"]; idx=item["row_idx"]; q=m._clean_question(row["question"]); kind=m._kind(q)
    queries=m._queries(q,kind)
    receipts=[]
    for qi,query in enumerate(queries,1):
        try:
            rr=m.rich_search(query,limit=7)
            receipts.append({"source":"BING_RSS","query_index":qi,"status":"PASS","result_count":len(rr)})
            summary["bing"]["ok"]+=1; summary["bing"]["results"]+=len(rr)
        except Exception as exc:
            receipts.append({"source":"BING_RSS","query_index":qi,"status":"FAILED",**err(exc)})
            summary["bing"]["failed"]+=1
        try:
            wr=m.wikipedia_search(query,limit=6)
            receipts.append({"source":"WIKIPEDIA","query_index":qi,"status":"PASS","result_count":len(wr)})
            summary["wikipedia"]["ok"]+=1; summary["wikipedia"]["results"]+=len(wr)
        except Exception as exc:
            receipts.append({"source":"WIKIPEDIA","query_index":qi,"status":"FAILED",**err(exc)})
            summary["wikipedia"]["failed"]+=1
    print(json.dumps({"row_idx":idx,"query_count":len(queries),"receipts":receipts,
                      "external_model_calls":0,"gold_accessed":False},sort_keys=True))
print("TRANSPORT_SUMMARY",json.dumps(summary,sort_keys=True))

# trigger corrected exact-policy transport replay
