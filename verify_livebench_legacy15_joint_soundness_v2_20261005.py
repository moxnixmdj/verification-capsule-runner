#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_legacy15_joint_soundness_v2_20261005"
sys.path.insert(0, str(SUB))
sys.path.insert(0, "/tmp/livebench/livebench/if_runner")

from canonical.runtime.livebench_frozen_active_legacy15_v1 import ACTIVE_IDS
from canonical.runtime.livebench_legacy15_joint_witness_v1 import solve
from instruction_following_eval import instructions_registry, instructions_util

DATA = ROOT / "livebench_instruction_following_predecessor.parquet"
EXPECTED_DATA_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
EXPECTED = {
    "livebench_legacy_visible_constraint_compiler_v1.py":"e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
    "livebench_legacy_visible_constraint_compiler_v4.py":"721207ba39d502e3f610289578e9d5bab78b1fcc",
    "livebench_frozen_active_legacy15_v1.py":"34440ee69322e9d519cbe656cb03c55683a8b9c6",
    "livebench_legacy15_joint_witness_v1.py":"8609c36c6ccba9da69cb793c2fd5fdf5d36f31ea",
}

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for name,sha in EXPECTED.items():
    got=git_blob_sha(SUB/"canonical"/"runtime"/name)
    assert got==sha,(name,got,sha)
assert hashlib.sha256(DATA.read_bytes()).hexdigest()==EXPECTED_DATA_SHA256

def clean(v):
    if isinstance(v,str):
        s=v.strip()
        if s and s[0] in "[{" and s[-1] in "]}":
            try:return clean(json.loads(s))
            except Exception:return v
        return v
    if isinstance(v,dict): return {str(k):clean(x) for k,x in v.items() if x is not None}
    if isinstance(v,(list,tuple)): return [clean(x) for x in v]
    return v

def prompt_from(row):
    turns=clean(row.get("turns"))
    if isinstance(turns,list) and len(turns)==1 and isinstance(turns[0],str): return turns[0]
    if isinstance(turns,str): return turns
    raise AssertionError(("PROMPT_UNRESOLVED",sorted(row)))

def ids_from(row):
    x=clean(row.get("instruction_id_list"))
    assert isinstance(x,list) and all(isinstance(i,str) for i in x),x
    return x

def kwargs_from(row,n):
    x=clean(row.get("kwargs"))
    assert isinstance(x,list) and len(x)==n,x
    return [({} if v is None else dict(v)) for v in x]

def exact_checks(ids,kwargs_list,response):
    results=[]
    for iid,kwargs in zip(ids,kwargs_list):
        obj=instructions_registry.INSTRUCTION_DICT[iid](iid)
        obj.build_description(**kwargs)
        ok=bool(obj.check_following(response))
        results.append((iid,ok))
    return results

# Source-domain soundness checks independent of historical row frequencies.
words=list(instructions_util.WORD_LIST)
assert len(words)==len(set(words))==1525
assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
wordset={w.lower() for w in words}
assert not any((w+"x").lower() in wordset for w in words)
for filler in ("zxqv","brnt","clmp","dgfk","hjwy","vvzz"):
    assert filler not in wordset

def historical_prompt(descriptions):
    return "Historical task request.\n-------\nPublic article body.\n-------\n" + " ".join(descriptions)

def source_case(specs, expect_candidate=True):
    descriptions=[]
    checkers=[]
    for iid,kwargs in specs:
        obj=instructions_registry.INSTRUCTION_DICT[iid](iid)
        desc=obj.build_description(**kwargs)
        descriptions.append(desc)
        checkers.append(obj)
    out=solve(historical_prompt(descriptions))
    if expect_candidate:
        assert out.get("status")=="PASS_CANDIDATE_JOINT_LEGACY15_WITNESS",(specs,out)
        response=out["response"]
        checks=[(obj.id,bool(obj.check_following(response))) for obj in checkers]
        assert all(ok for _,ok in checks),(specs,response,checks)
    else:
        assert out.get("status")=="FAIL_CLOSED",(specs,out)
    return out

source_case([
    ("keywords:existence",{"keywords":["cat"]}),
    ("keywords:forbidden_words",{"forbidden_words":["response","cat"]}),
    ("detectable_format:json_format",{}),
])
source_case([
    ("keywords:forbidden_words",{"forbidden_words":["alpha","beta","response"]}),
    ("combination:two_responses",{}),
])
source_case([
    ("keywords:existence",{"keywords":["cat"]}),
    ("keywords:forbidden_words",{"forbidden_words":["cat","catx","catxx","catxxx","catxxxx"]}),
])
source_case([
    ("length_constraints:number_sentences",{"num_sentences":1,"relation":"less than"}),
],expect_candidate=False)
source_case([
    ("length_constraints:number_sentences",{"num_sentences":2,"relation":"less than"}),
    ("detectable_content:postscript",{"postscript_marker":"P.S."}),
    ("startend:end_checker",{"end_phrase":"Any other questions?"}),
],expect_candidate=False)

rows=pq.read_table(DATA).to_pylist()
assert len(rows)==200
active=set(ACTIVE_IDS)
eligible=[]
for idx,row in enumerate(rows):
    ids=ids_from(row)
    if set(ids)<=active:
        eligible.append((idx,row,ids))

stats=Counter()
false_positive=[]
solver_fail=[]
exact_pass=[]
for idx,row,ids in eligible:
    prompt=prompt_from(row)
    kwargs_list=kwargs_from(row,len(ids))
    out=solve(prompt)
    stats["eligible"]+=1
    stats["eligible_constraints"]+=len(ids)
    if out.get("status")!="PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
        stats["solver_fail_closed"]+=1
        solver_fail.append({"row":idx,"ids":ids,"error":out.get("error")})
        continue
    stats["solver_candidate"]+=1
    response=out["response"]
    checks=exact_checks(ids,kwargs_list,response)
    bad=[iid for iid,ok in checks if not ok]
    if bad:
        stats["false_positive_rows"]+=1
        false_positive.append({
            "row":idx,
            "ids":ids,
            "route":out.get("route"),
            "failed_checkers":bad,
            "response":response,
        })
    else:
        stats["exact_full_pass_rows"]+=1
        exact_pass.append(idx)

report={
    "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_SOUNDNESS_V2_INDEPENDENT_REPLAY",
    "dataset_revision":"4f7ab12f0d47848da31de92bd7cc3d7d4acfe695",
    "dataset_sha256":EXPECTED_DATA_SHA256,
    "historical_rows":len(rows),
    "eligible_active15_only_rows":stats["eligible"],
    "solver_candidate_rows":stats["solver_candidate"],
    "solver_fail_closed_rows":stats["solver_fail_closed"],
    "exact_full_pass_rows":stats["exact_full_pass_rows"],
    "false_positive_rows":stats["false_positive_rows"],
    "false_positive_sample":false_positive[:20],
    "fail_closed_sample":solver_fail[:20],
    "active_terminal_rows_read":0,
    "acceptance_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0,
    "scope":"CLEAN_HISTORICAL_ACTIVE15_ONLY_ROWS__FROZEN_EXACT_CHECKER_EXECUTION__NOT_ACTIVE_TERMINAL_SCORE",
}
print(json.dumps(report,ensure_ascii=False,sort_keys=True))

# The current solver claims PASS_CANDIDATE only when it believes it constructed
# a joint witness. Any exact checker rejection is therefore a sound falsification.
assert not false_positive, json.dumps(false_positive[:10],ensure_ascii=False)
