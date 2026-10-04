#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path
from collections import Counter
import pyarrow.parquet as pq

HF_URL="https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet"
HF_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
TARGET_RELEASE="2026-06-25"
RELEASES={"2024-06-24","2024-07-26","2024-08-31","2024-11-25","2025-04-02","2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25"}

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=45) as r:return r.read()

def h(s): return hashlib.sha256(s.encode()).hexdigest()

def main():
    b=fetch(HF_URL); assert hashlib.sha256(b).hexdigest()==HF_SHA256
    Path("/tmp/if.parquet").write_bytes(b)
    cols=["question_id","task","livebench_release_date","livebench_removal_date"]
    rows=pq.read_table("/tmp/if.parquet",columns=cols).to_pylist()
    active=[]
    for r in rows:
        rd=r["livebench_release_date"]
        rd=rd.strftime("%Y-%m-%d") if hasattr(rd,"strftime") else str(rd)
        rem=r["livebench_removal_date"] or ""
        if rd in RELEASES and (rem=="" or rem>TARGET_RELEASE):
            active.append({**r,"rd":rd})
    assert len(active)==200
    ids={str(r["question_id"]) for r in active}
    assert all(len(x)==64 and all(c in "0123456789abcdef" for c in x) for x in ids)

    # Generic public LiveBench merge rule observed in apply_edits_to_code_completion.py:
    # sha256(f"{path_string}/{index}-{release_date}").
    # Search only a predeclared structural grammar. No prompt/kwargs/instruction bytes.
    tasks=sorted({r["task"] for r in active})
    roots=[
      "live_bench/instruction_following/{task}",
      "live_bench/instruction_following",
      "instruction_following/{task}",
      "instruction_following",
      "livebench/instruction_following/{task}",
      "livebench/instruction_following",
      "data/live_bench/instruction_following/{task}",
      "data/live_bench/instruction_following",
    ]
    date_modes={
      "row_release": sorted({r["rd"] for r in active}),
      "target_release": [TARGET_RELEASE],
      "known_releases": sorted(RELEASES),
    }
    results=[]
    for root in roots:
        root_values=[root.format(task=t) for t in tasks] if "{task}" in root else [root]
        for date_mode,dates in date_modes.items():
            generated=set()
            for rv in root_values:
                for d in dates:
                    for i in range(1000):
                        generated.add(h(f"{rv}/{i}-{d}"))
            hits=len(ids & generated)
            results.append({"path_pattern":root,"date_mode":date_mode,"hit_count":hits,"covers_all_active":hits==len(ids)})
    results.sort(key=lambda x:(-x["hit_count"],x["path_pattern"],x["date_mode"]))

    # Also test whether each row binds using its task + one of two deterministic
    # ordinal conventions, without revealing IDs or row contents.
    per_row=[]
    counters=Counter()
    global_i=0
    for r in active:
        task_i=counters[r["task"]]; counters[r["task"]]+=1
        for root in roots:
            rv=root.format(task=r["task"]) if "{task}" in root else root
            for idx_name,idx in [("global_active_ordinal",global_i),("per_task_active_ordinal",task_i)]:
                for dname,d in [("row_release",r["rd"]),("target_release",TARGET_RELEASE)]:
                    if h(f"{rv}/{idx}-{d}")==str(r["question_id"]):
                        per_row.append((root,idx_name,dname))
        global_i+=1
    combo_counts=Counter(per_row)

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_QUESTION_ID_HASH_LINEAGE_AUDIT_V1",
      "status":"PASS_AUDIT_COMPLETED",
      "source_rule":"SHA256(PATH_STRING_SLASH_INDEX_HYPHEN_RELEASE_DATE)",
      "hf_sha256":HF_SHA256,
      "active_rows":len(active),
      "task_counts":dict(Counter(r["task"] for r in active)),
      "release_counts":dict(Counter(r["rd"] for r in active)),
      "top_universe_candidates":results[:12],
      "per_row_formula_match_counts":[
        {"path_pattern":k[0],"index_mode":k[1],"date_mode":k[2],"match_count":v}
        for k,v in combo_counts.most_common()
      ],
      "prompt_or_turns_loaded":False,
      "kwargs_loaded":False,
      "instruction_text_loaded":False,
      "question_ids_emitted":False,
      "acceptance_credit_delta":0
    }
    Path("livebench_question_id_hash_lineage_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
