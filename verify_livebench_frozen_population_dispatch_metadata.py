#!/usr/bin/env python3
from __future__ import annotations
import datetime, hashlib, json, urllib.request
from pathlib import Path
import pyarrow.parquet as pq

URL="https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet?download=true"
SHA="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
SIZE=537024
FROZEN_RELEASE="2026-06-25"
BOUNDARY="2025-11-25"
VALID={"2024-06-24","2024-07-26","2024-08-31","2024-11-25","2025-04-02","2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25"}

def iso(v):
    if isinstance(v,(datetime.date,datetime.datetime)): return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v)[:10]

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=Path("frozen_instruction_following.parquet")
    urllib.request.urlretrieve(URL,p)
    assert p.stat().st_size==SIZE
    assert digest(p)==SHA
    table=pq.read_table(p,columns=["livebench_release_date","livebench_removal_date","category"])
    rows=table.to_pylist()
    selected=[]
    hist={}
    for q in rows:
        rel=iso(q.get("livebench_release_date"))
        rem=iso(q.get("livebench_removal_date"))
        if rel not in VALID: continue
        if rem and rem <= FROZEN_RELEASE: continue
        selected.append((rel,rem,str(q.get("category") or "")))
        hist[rel]=hist.get(rel,0)+1
    assert len(rows)==400
    assert len(selected)==200
    assert all(c=="instruction_following" for _,_,c in selected)
    legacy=sum(r < BOUNDARY for r,_,_ in selected)
    modern=sum(r >= BOUNDARY for r,_,_ in selected)
    assert legacy==200 and modern==0,(legacy,modern,hist)
    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_FROZEN_POPULATION_DISPATCH_METADATA_VERIFICATION_V1",
      "status":"PASS__200_OF_200_LEGACY_IFEVAL__ZERO_MODERN_IFBENCH",
      "frozen_dataset":{"revision":"0868379c4b5cf62aeacaf8be4f08fced815c81bb","parquet_sha256":SHA,"parquet_bytes":SIZE,"raw_rows":len(rows)},
      "filter":{"livebench_release":FROZEN_RELEASE,"selected_rows":len(selected),"release_histogram":dict(sorted(hist.items()))},
      "dispatch":{"boundary":BOUNDARY,"legacy_ifeval_rows":legacy,"modern_ifbench_rows":modern},
      "deductions":[
        "FROZEN_200_CASE_POPULATION_HAS_ZERO_MODERN_IFBENCH_ROWS",
        "MODERN_58_CHECKER_IFBENCH_REPAIR_IS_NOT_ON_THE_CRITICAL_PATH_FOR_THIS_FROZEN_PREDICATE",
        "ALL_200_CASES_USE_THE_LEGACY_INSTRUCTION_FOLLOWING_EVALUATOR"
      ],
      "firewall":{"columns_read":["livebench_release_date","livebench_removal_date","category"],"prompt_or_turns_read":False,"kwargs_read":False,"instruction_ids_read":False,"terminal_case_content_exposed":False},
      "accounting":{"incremental_spend_usd":0,"new_terminal_case_content_consumed":0,"acceptance_credit_delta":0}
    }
    Path("livebench_frozen_population_dispatch_metadata_receipt.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
