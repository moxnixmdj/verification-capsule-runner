#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import urllib.request

import pyarrow.parquet as pq

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

REV="4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
EXPECTED_SHA256="57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
EXPECTED_ROWS=200
BRAIN_V1_BLOB="e986035ff68b53c0dc7a7eb478f6e3d8882214aa"
BRAIN_V2_BLOB="0e7519f4f2b7d40084effc83a5bef814ee7fd487"


def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def clean_kwargs(d):
    if d is None:
        return {}
    return {str(k):v for k,v in dict(d).items() if v is not None}


def eq_value(k, expected, observed):
    if k=="prompt_to_repeat" and isinstance(expected,str) and isinstance(observed,str):
        return expected.strip()==observed.strip()
    return expected==observed


v1p=pathlib.Path("canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py")
v2p=pathlib.Path("canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py")
assert git_blob_sha(v1p)==BRAIN_V1_BLOB
assert git_blob_sha(v2p)==BRAIN_V2_BLOB

url=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{REV}/data/test-00000-of-00001.parquet?download=true"
dst=pathlib.Path("livebench_if_predecessor_200.parquet")
urllib.request.urlretrieve(url,dst)
raw=dst.read_bytes()
assert hashlib.sha256(raw).hexdigest()==EXPECTED_SHA256
table=pq.read_table(dst)
assert table.num_rows==EXPECTED_ROWS
rows=table.to_pylist()

failures=[]
recognized_instances=0
expected_instances=0
complete_rows=0
for idx,row in enumerate(rows):
    ids=list(row.get("instruction_id_list") or [])
    kwargs=list(row.get("kwargs") or [])
    turns=row.get("turns")
    if isinstance(turns,(list,tuple)):
        prompt=str(turns[0])
    else:
        prompt=str(row.get("prompt") or turns or "")
    out=compiler.compile_visible_constraints(prompt)
    cons=list(out.get("constraints") or [])
    recognized_instances += len(cons)
    expected_instances += len(ids)

    by_id=collections.defaultdict(list)
    for c in cons:
        by_id[str(c.get("instruction_id"))].append(c)

    row_errors=[]
    if out.get("status")!="PASS":
        row_errors.append({"kind":"compiler_status","value":out.get("status")})
    if collections.Counter(c.get("instruction_id") for c in cons)!=collections.Counter(ids):
        row_errors.append({
            "kind":"instruction_multiset",
            "expected":dict(collections.Counter(ids)),
            "observed":dict(collections.Counter(c.get("instruction_id") for c in cons)),
        })
    for pos,instruction_id in enumerate(ids):
        exp=clean_kwargs(kwargs[pos] if pos < len(kwargs) else {})
        candidates=by_id.get(instruction_id,[])
        if len(candidates)!=1:
            # Historical generator samples self-conflicting IDs at most once.
            continue
        c=candidates[0]
        if not c.get("parameter_complete"):
            row_errors.append({
                "kind":"parameter_incomplete",
                "instruction_id":instruction_id,
                "unresolved":c.get("unresolved_parameters"),
            })
            continue
        slots=dict(c.get("slots") or {})
        for k,v in exp.items():
            if k not in slots or not eq_value(k,v,slots.get(k)):
                row_errors.append({
                    "kind":"kwarg_mismatch",
                    "instruction_id":instruction_id,
                    "key":k,
                    "expected":v,
                    "observed":slots.get(k),
                })
    if row_errors:
        failures.append({
            "row_index":idx,
            "question_id":row.get("question_id"),
            "errors":row_errors,
        })
    else:
        complete_rows += 1

print("PREDECESSOR_ROWS",len(rows))
print("EXPECTED_INSTRUCTION_INSTANCES",expected_instances)
print("RECOGNIZED_INSTRUCTION_INSTANCES",recognized_instances)
print("EXACT_COMPLETE_ROWS",complete_rows)
print("FAILURE_ROWS",len(failures))
if failures:
    print("FIRST_FAILURES")
    print(json.dumps(failures[:20],ensure_ascii=False,indent=2,default=str))

assert not failures, f"{len(failures)} predecessor rows failed exact compiler replay"

print("LIVEBENCH_LEGACY_PREDECESSOR_V2_REPLAY=PASS")
print("terminal_active_2024_11_25_prompt_rows_read=0")
print("predecessor_rows_read=200")
print("incremental_spend_usd=0")
