#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, re, urllib.request
from datetime import datetime
from pathlib import Path
import pyarrow.parquet as pq

DATASET_REV="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
PARQUET_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
DATA_URL=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{DATASET_REV}/data/test-00000-of-00001.parquet"
GT_URL=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/gen_ground_truth_judgment.py"
COMMON_URL=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/common.py"
FROZEN_RELEASE="2026-06-25"

def fetch(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-dispatch-verifier"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def main()->int:
    raw=fetch(DATA_URL)
    got=hashlib.sha256(raw).hexdigest()
    assert got==PARQUET_SHA256,(got,PARQUET_SHA256)

    # Deliberately project ONLY routing metadata. Prompt, kwargs, IDs, and task
    # content are never deserialized, logged, or used.
    table=pq.read_table(
        io.BytesIO(raw),
        columns=["livebench_release_date","livebench_removal_date"],
    )
    release=table.column("livebench_release_date").to_pylist()
    removal=table.column("livebench_removal_date").to_pylist()

    gt=fetch(GT_URL).decode("utf-8")
    common=fetch(COMMON_URL).decode("utf-8")

    m=re.search(r'livebench_release_date", ""\) < "(\d{4}-\d{2}-\d{2})"',gt)
    assert m,"dispatch boundary not found"
    boundary=m.group(1)
    assert boundary=="2025-11-25",boundary

    rm=re.search(r'LIVE_BENCH_RELEASES\s*=\s*\{([^}]+)\}',common)
    assert rm,"release set not found"
    allowed=set(re.findall(r'"(\d{4}-\d{2}-\d{2})"',rm.group(1)))
    assert FROZEN_RELEASE in allowed

    def dstr(x):
        if isinstance(x,datetime): return x.strftime("%Y-%m-%d")
        if hasattr(x,"strftime"): return x.strftime("%Y-%m-%d")
        return str(x)[:10]

    active=[]
    for rel,rem in zip(release,removal):
        rels=dstr(rel)
        rems="" if rem is None else str(rem)
        if rels not in allowed:
            continue
        if rems=="" or rems>FROZEN_RELEASE:
            active.append(rels)

    assert len(active)==200,len(active)
    min_rel=min(active)
    max_rel=max(active)
    modern=[x for x in active if x>=boundary]
    legacy=[x for x in active if x<boundary]
    assert len(modern)==0,modern
    assert len(legacy)==200,len(legacy)

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_FROZEN_DISPATCH_REACHABILITY_VERIFICATION_V1",
      "status":"PASS",
      "frozen":{
        "benchmark_release":FROZEN_RELEASE,
        "dataset_revision":DATASET_REV,
        "dataset_parquet_sha256":got,
        "livebench_commit":LIVEBENCH_COMMIT,
      },
      "projection_policy":{
        "deserialized_columns":["livebench_release_date","livebench_removal_date"],
        "prompt_column_read":False,
        "kwargs_column_read":False,
        "instruction_id_list_column_read":False,
        "case_ids_read":False,
        "response_content_read":False,
      },
      "scorer_dispatch":{
        "legacy_if_release_date_before":boundary,
        "active_population":len(active),
        "active_release_date_min":min_rel,
        "active_release_date_max":max_rel,
        "legacy_reachable_cases":len(legacy),
        "modern_ifbench_reachable_cases":len(modern),
        "modern_ifbench_reachability_probability":0.0,
      },
      "proved":[
        "ALL_200_FROZEN_ACTIVE_CASES_ROUTE_TO_LEGACY_INSTRUCTION_FOLLOWING_EVALUATOR",
        "ZERO_FROZEN_ACTIVE_CASES_ROUTE_TO_IFBENCH_MODERN_EVALUATOR",
        "MODERN_IFBENCH_RATIO_OVERLAP_REPAIR_CANNOT_CHANGE_FROZEN_LIVEBENCH_IF_SCORE",
      ],
      "hard_nonclaims":[
        "NO_LIVEBENCH_SCORE_PROVED",
        "NO_TERMINAL_PROMPT_CONTENT_READ",
        "NO_ACCEPTANCE_OR_PROMOTION_CREDIT",
        "NO_LEGACY_SOLVER_CORRECTNESS_PROVED",
      ],
    }
    Path("livebench_frozen_dispatch_reachability_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
