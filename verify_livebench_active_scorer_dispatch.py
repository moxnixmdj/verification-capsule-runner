#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, urllib.request
from collections import Counter
from pathlib import Path

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
HF_REVISION="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
PARQUET_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
PARQUET_BYTES=537024
RELEASE="2026-06-25"
CUTOFF="2025-11-25"
RELEASES={
 "2024-07-26","2024-06-24","2024-08-31","2024-11-25","2025-04-02",
 "2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25"
}
GEN_URL=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/gen_ground_truth_judgment.py"
HF_URL=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{HF_REVISION}/data/test-00000-of-00001.parquet"

def fetch(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def main()->int:
    import pyarrow.parquet as pq

    gen_raw=fetch(GEN_URL)
    gen=gen_raw.decode("utf-8")
    required=[
      "old_instruction_following_matches = [m for m in matches if m.question.get('category') == 'instruction_following' and m.question.get(\"livebench_release_date\", \"\") < \"2025-11-25\"]",
      "normal_matches = [m for m in matches if m not in agentic_coding_matches and m not in old_instruction_following_matches]",
      "scores = instruction_following_process_results(if_questions, if_answers, task_name, model_id, debug)",
    ]
    for x in required:
        assert x in gen, x

    data=fetch(HF_URL)
    assert len(data)==PARQUET_BYTES,(len(data),PARQUET_BYTES)
    assert hashlib.sha256(data).hexdigest()==PARQUET_SHA256
    p=Path("/tmp/livebench_if.parquet")
    p.write_bytes(data)

    # Deliberately metadata-only: no turns, prompt, kwargs, or instruction IDs.
    cols=["question_id","task","livebench_release_date","livebench_removal_date"]
    rows=pq.read_table(p,columns=cols).to_pylist()
    assert len(rows)==400
    assert len({r["question_id"] for r in rows})==400

    active=[]
    for r in rows:
        rd=r["livebench_release_date"]
        rd=rd.strftime("%Y-%m-%d") if hasattr(rd,"strftime") else str(rd)
        rem=r["livebench_removal_date"] or ""
        if rd in RELEASES and (rem=="" or rem>RELEASE):
            active.append({**r,"release_date_normalized":rd})
    assert len(active)==200

    by_release=Counter(r["release_date_normalized"] for r in active)
    by_task=Counter(r["task"] for r in active)
    old=sum(1 for r in active if r["release_date_normalized"] < CUTOFF)
    modern=len(active)-old

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_ACTIVE_SCORER_DISPATCH_METADATA_VERIFICATION_V1",
      "status":"PASS",
      "pinned":{
        "livebench_commit":LIVEBENCH_COMMIT,
        "hf_revision":HF_REVISION,
        "parquet_sha256":PARQUET_SHA256,
        "parquet_bytes":PARQUET_BYTES,
        "selected_release":RELEASE,
        "dispatch_cutoff":CUTOFF,
        "gen_ground_truth_judgment_sha256":hashlib.sha256(gen_raw).hexdigest(),
      },
      "read_scope":{
        "parquet_columns":cols,
        "prompt_or_turn_text_read":False,
        "kwargs_read":False,
        "instruction_id_list_read":False,
      },
      "active_population":{
        "total":len(active),
        "by_release_date":dict(sorted(by_release.items())),
        "by_task":dict(sorted(by_task.items())),
        "legacy_instruction_following_path_count":old,
        "ifbench_path_count":modern,
      },
      "verified_dispatch_rule":{
        "legacy":"instruction_following category AND livebench_release_date < 2025-11-25 -> instruction_following_process_results",
        "modern":"remaining instruction_following rows -> play_a_match_gt -> ifbench_process_results",
      },
      "deduction":(
        "ACTIVE_2026_06_25_POPULATION_SCORER_ROUTE_PARTITION_IS_FIXED_BY_RELEASE_DATE_METADATA;"
        f"LEGACY={old};IFBENCH={modern}"
      ),
      "hard_nonclaims":[
        "NO_PROMPT_OR_TURN_TEXT_READ",
        "NO_KWARGS_OR_INSTRUCTION_IDS_READ",
        "NO_BRAIN_SCORE",
        "NO_ACCEPTANCE_CREDIT",
        "NO_CLAIM_THAT_SCORER_ROUTE_ALONE_CHANGES_THE_FROZEN_CANDIDATE_ZERO_RESPONSE_RESULT"
      ],
      "accounting":{"incremental_spend_usd":0,"terminal_cases_consumed":0}
    }
    Path("livebench_active_scorer_dispatch_receipt.json").write_text(
      json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
