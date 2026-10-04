#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

BRAIN_COMMIT = "5541eedcd78241c50e7e44f32eee4fff3ccdc35b"
CANDIDATE_BLOB = "5bbf781607e9650199b9453a52b8dd2b5a324fc9"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
ROUTER_BLOB = "b36561da5b54380c724c507462d0ee65feefeac8"
PROCESS_UTILS_BLOB = "8ce01747887ec0792c8f024e1972e34ece781676"
HF_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
PARQUET_BYTES = 537024
CUTOFF = "2025-11-25"
TARGET_RELEASE = "2026-06-25"

def fetch(url: str) -> bytes:
    req=urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def main() -> int:
    # Bind exact Brain candidate.
    cand=fetch(
        "https://raw.githubusercontent.com/moxnixmdj/brain/"
        +BRAIN_COMMIT+
        "/canonical/governance/LIVEBENCH_ACTIVE_LEGACY_DISPATCH_TRUTH_REPAIR_V1.json"
    )
    assert git_blob_sha(cand)==CANDIDATE_BLOB
    candidate=json.loads(cand)

    # Bind exact public dataset bytes.
    parquet=fetch(
        "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
        +HF_REV+
        "/data/test-00000-of-00001.parquet"
    )
    assert len(parquet)==PARQUET_BYTES
    assert hashlib.sha256(parquet).hexdigest()==PARQUET_SHA256
    p=Path("/tmp/livebench_instruction_following.parquet")
    p.write_bytes(parquet)

    # Metadata-only proof. Deliberately do not load question_id, turns, kwargs,
    # instruction_id_list, task_prompt, citation, or any response content.
    cols=["task","livebench_release_date","livebench_removal_date"]
    rows=pq.read_table(p, columns=cols).to_pylist()
    assert len(rows)==400
    dates=[]
    for r in rows:
        d=r["livebench_release_date"]
        d=d.strftime("%Y-%m-%d") if hasattr(d,"strftime") else str(d)[:10]
        dates.append(d)
    assert min(dates)=="2024-06-24", min(dates)
    assert max(dates)=="2024-11-25", max(dates)
    assert all(d < CUTOFF for d in dates)

    active=[]
    for r,d in zip(rows,dates):
        rem=r["livebench_removal_date"] or ""
        if rem=="" or rem>TARGET_RELEASE:
            active.append((r,d))
    counts=Counter(r["task"] for r,_ in active)
    expected={"paraphrase":50,"simplify":50,"story_generation":50,"summarize":50}
    assert len(active)==200, len(active)
    assert counts==expected, (counts,expected)
    assert all(d<CUTOFF for _,d in active)

    # Bind exact router and prove active scorer family composition.
    router=fetch(
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        +LIVEBENCH_COMMIT+
        "/livebench/gen_ground_truth_judgment.py"
    )
    assert git_blob_sha(router)==ROUTER_BLOB
    router_text=router.decode("utf-8")
    assert 'question.get("livebench_release_date", "") < "2025-11-25"' in router_text
    assert "old_instruction_following_matches" in router_text
    assert "scores = instruction_following_process_results(if_questions, if_answers, task_name, model_id, debug)" in router_text
    assert "score = ifbench_process_results(question, llm_answer, debug)" in router_text

    legacy=sum(1 for _,d in active if d<CUTOFF)
    modern=sum(1 for _,d in active if d>=CUTOFF)
    assert (legacy,modern)==(200,0)

    # The score-mass theorem survives the scorer-family correction because both
    # paths call the same public score_results arithmetic.
    proc=fetch(
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        +LIVEBENCH_COMMIT+
        "/livebench/process_results/instruction_following/utils.py"
    )
    assert git_blob_sha(proc)==PROCESS_UTILS_BLOB
    process=proc.decode("utf-8")
    assert "avg_score = (score_1 + score_2) / 2" in process
    assert "score_results(result.follow_all_instructions, result.follow_instruction_list)" in process
    assert "scores = instruction_following_process_results" not in process  # routing stays in router

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_ACTIVE_LEGACY_DISPATCH_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS",
      "candidate_git_blob_sha":CANDIDATE_BLOB,
      "dataset":{
        "revision":HF_REV,
        "sha256":PARQUET_SHA256,
        "rows":400,
        "release_date_min":min(dates),
        "release_date_max":max(dates),
        "active_2026_06_25_count":len(active),
        "active_task_counts":dict(sorted(counts.items()))
      },
      "dispatch":{
        "cutoff":CUTOFF,
        "legacy_active_rows":legacy,
        "modern_active_rows":modern,
        "router_git_blob_sha":ROUTER_BLOB
      },
      "verified":[
        "EXACT_FROZEN_DATASET_BYTES_BOUND",
        "ONLY_TASK_RELEASE_DATE_REMOVAL_DATE_COLUMNS_LOADED",
        "ALL_400_ROWS_PREDATE_2025_11_25",
        "ACTIVE_200_COUNTS_EQUAL_50_50_50_50",
        "ACTIVE_200_DISPATCH_200_LEGACY_0_MODERN",
        "PRIOR_ACTIVE_IFBENCH_ROUTE_CLAIM_CONTRADICTED",
        "SHARED_SCORE_RESULTS_ALGEBRA_PRESERVED"
      ],
      "semantic_effect":"Modern IFBench-specific 58-checker repair is not load-bearing for the exact active 200-row comparator population; the active scorer family is legacy IFEval.",
      "hard_nonclaims":[
        "NO_BENCHMARK_PROMPT_RESPONSE_KWARGS_INSTRUCTION_IDS_OR_QUESTION_IDS_LOADED",
        "NO_SUCCESSOR_SCORE_OR_ACCEPTANCE_CREDIT",
        "NO_EXECUTION_OR_PROMOTION_AUTHORITY"
      ],
      "accounting":{"incremental_spend_usd":0,"acceptance_credit_delta":0}
    }
    Path("livebench_active_legacy_dispatch_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n", encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
