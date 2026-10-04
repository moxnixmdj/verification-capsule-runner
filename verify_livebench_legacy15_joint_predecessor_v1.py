#!/usr/bin/env python3
from __future__ import annotations
import collections
import hashlib
import importlib
import json
import pathlib
import sys
import urllib.request

import pyarrow.parquet as pq

from canonical.runtime import livebench_frozen_active_legacy15_v1 as active15
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as generator

REV="4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
DATA_SHA256="57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
DATA_BYTES=277319
ROWS=200
LB_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
SOURCE_FILES={
    "instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
}
BRAIN_BLOBS={
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py":"34f4df9f0bd265fc555686bd251a264e446d4c04",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py":"721207ba39d502e3f610289578e9d5bab78b1fcc",
    "canonical/runtime/livebench_frozen_active_legacy15_v1.py":"34440ee69322e9d519cbe656cb03c55683a8b9c6",
    "canonical/runtime/livebench_legacy15_composition_partition_v1.py":"b817b4f63f4e98c2705f221c7a4abd8e571f9d80",
    "canonical/runtime/livebench_legacy15_joint_candidate_generator_v1.py":"8c8e574af8a275a96e2df2f789ebe18cdbb3b162",
}

def git_blob_bytes(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def git_blob_path(path:str)->str:
    return git_blob_bytes(pathlib.Path(path).read_bytes())

for path,sha in BRAIN_BLOBS.items():
    got=git_blob_path(path)
    assert got==sha,(path,got,sha)

pkgroot=pathlib.Path("exact_livebench")
pkg=pkgroot/"instruction_following_eval"
pkg.mkdir(parents=True,exist_ok=True)
(pkg/"__init__.py").write_text("")
for name,sha in SOURCE_FILES.items():
    url=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LB_COMMIT}/livebench/if_runner/instruction_following_eval/{name}"
    raw=urllib.request.urlopen(url,timeout=30).read()
    assert git_blob_bytes(raw)==sha,(name,git_blob_bytes(raw),sha)
    (pkg/name).write_bytes(raw)
sys.path.insert(0,str(pkgroot.resolve()))
registry=importlib.import_module("instruction_following_eval.instructions_registry")

url=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{REV}/data/test-00000-of-00001.parquet?download=true"
dst=pathlib.Path("predecessor.parquet")
urllib.request.urlretrieve(url,dst)
raw=dst.read_bytes()
assert len(raw)==DATA_BYTES,(len(raw),DATA_BYTES)
assert hashlib.sha256(raw).hexdigest()==DATA_SHA256
rows=pq.read_table(dst).to_pylist()
assert len(rows)==ROWS

active=set(active15.ACTIVE_IDS)
eligible=0
solved=0
compile_fail=0
generation_fail=0
checker_fail_rows=0
total_candidates=0
max_candidates=0
mode_hist=collections.Counter()
set_hist=collections.Counter()
failure_samples=[]

def check_candidate(prompt, ids, kwargs, response):
    per=[]
    for pos,iid in enumerate(ids):
        cls=registry.INSTRUCTION_DICT[iid]
        inst=cls(iid)
        kw={str(k):v for k,v in dict(kwargs[pos] or {}).items() if v is not None}
        inst.build_description(**kw)
        args=inst.get_instruction_args()
        if args and "prompt" in args:
            inst.build_description(prompt=prompt)
        ok=bool(response.strip()) and bool(inst.check_following(response))
        per.append((iid,ok))
        if not ok:
            return False,per
    return True,per

for idx,row in enumerate(rows):
    ids=[str(x) for x in (row.get("instruction_id_list") or [])]
    if not ids or not set(ids).issubset(active):
        continue
    eligible+=1
    set_hist[tuple(sorted(ids))]+=1
    turns=list(row.get("turns") or [])
    assert len(turns)==1
    prompt=str(turns[0])
    kwargs=list(row.get("kwargs") or [])
    assert len(kwargs)==len(ids)

    compiled=compiler.compile_visible_constraints(prompt)
    constraints=list(compiled.get("constraints") or [])
    got_ids=[str(c.get("instruction_id")) for c in constraints]
    if compiled.get("status")!="PASS" or collections.Counter(got_ids)!=collections.Counter(ids):
        compile_fail+=1
        if len(failure_samples)<20:
            failure_samples.append({
                "row":idx,"kind":"compile","expected_ids":ids,"got_ids":got_ids,
                "status":compiled.get("status"),
            })
        continue

    gen=generator.generate(constraints,max_candidates=96)
    candidates=list(gen.get("candidates") or [])
    mode_hist[str(gen.get("mode") or gen.get("status"))]+=1
    total_candidates += len(candidates)
    max_candidates=max(max_candidates,len(candidates))
    if not candidates:
        generation_fail+=1
        if len(failure_samples)<20:
            failure_samples.append({"row":idx,"kind":"generate","ids":ids,"gen":gen})
        continue

    ok_any=False
    last_checks=None
    for response in candidates:
        ok,checks=check_candidate(prompt,ids,kwargs,str(response))
        last_checks=checks
        if ok:
            ok_any=True
            break
    if ok_any:
        solved+=1
    else:
        checker_fail_rows+=1
        if len(failure_samples)<20:
            failure_samples.append({
                "row":idx,"kind":"checker","ids":ids,
                "mode":gen.get("mode"),"candidate_count":len(candidates),
                "last_checks":last_checks,
            })

print("LIVEBENCH_LEGACY15_CANDIDATE_PREDECESSOR_REPLAY")
print("eligible_rows",eligible)
print("solved_rows",solved)
print("compile_fail_rows",compile_fail)
print("generation_fail_rows",generation_fail)
print("checker_fail_rows",checker_fail_rows)
print("total_candidates",total_candidates)
print("max_candidates_per_row",max_candidates)
print("route_hist",json.dumps(dict(mode_hist),sort_keys=True))
print("distinct_constraint_sets",len(set_hist))
if failure_samples:
    print("failure_samples",json.dumps(failure_samples,ensure_ascii=False,indent=2,default=str))

assert eligible>0
assert compile_fail==0,compile_fail
assert generation_fail==0,generation_fail
assert checker_fail_rows==0,checker_fail_rows
assert solved==eligible,(solved,eligible)

print("LIVEBENCH_LEGACY15_CANDIDATE_PREDECESSOR_REPLAY=PASS")
print("active_terminal_prompt_rows_read=0")
print("predecessor_rows_read=200")
print("incremental_spend_usd=0")
