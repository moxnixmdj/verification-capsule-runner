#!/usr/bin/env python3
import json,urllib.parse,urllib.request
from canonical.runtime.hle_native_open_domain_research_v5 import propose
URL="https://datasets-server.huggingface.co/rows?"+urllib.parse.urlencode({
 "dataset":"ai-safety-institute/trivia_qa_verified","config":"default","split":"validation","offset":25,"length":10})
with urllib.request.urlopen(urllib.request.Request(URL,headers={"User-Agent":"ProjectBrain-TransportProbe/1.0"}),timeout=30) as r:
 rows=json.loads(r.read().decode())["rows"]
for item in rows:
 row=item["row"]; idx=item["row_idx"]
 o=propose(task_id=f"diag_{idx}",question=row["question"],has_nonempty_image_payload=False)
 print(json.dumps({
  "row_idx":idx,"status":o.get("status"),"query_count":o.get("query_count"),
  "evidence_item_count":o.get("evidence_item_count"),
  "query_receipts":o.get("query_receipts",[]),
  "external_model_calls":o.get("external_model_calls",0),
  "gold_accessed":o.get("gold_accessed",False)
 },sort_keys=True))
