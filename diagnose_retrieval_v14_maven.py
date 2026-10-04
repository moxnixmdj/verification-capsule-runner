#!/usr/bin/env python3
import json
from canonical.runtime import retrieval_live_provider_arena_v14 as v14

out=[]
for row in v14.rows():
    if row["episode_id"] not in {"MAVEN_COLLECTIONS","MAVEN_JSON_BIND"}:
        continue
    b=v14.bridge(str(row["query"]),timeout=20.0,max_repos=20,max_poms=24)
    out.append({
        "episode_id":row["episode_id"],
        "query":row["query"],
        "generated_queries":b["queries"],
        "repository_candidates":b["repository_candidates"][:30],
        "coordinates":b["coordinates"][:120],
        "search_traces":b["search_traces"],
        "repository_manifest_traces":[{
            "repository":x.get("repository"),
            "status":x.get("status"),
            "pom_files":x.get("pom_files"),
            "coordinates":x.get("coordinates"),
            "error":x.get("error")
        } for x in b["repository_manifest_traces"]]
    })
print("V14_DIAGNOSTIC",json.dumps(out,ensure_ascii=False,sort_keys=True))
