#!/usr/bin/env python3
from __future__ import annotations
import hashlib, pathlib, re, urllib.request
import pyarrow.parquet as pq

DATASET_REV="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
EXPECTED_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
EXPECTED_BYTES=537024
EXPECTED_ROWS=400
EXPECTED_MAX_RELEASE="2024-11-25"
DISPATCH_BOUNDARY="2025-11-25"
EXECUTOR=pathlib.Path("execute_livebench_if_replay72_v4_candidate.py")
EXECUTOR_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def norm_date(x)->str:
    if hasattr(x,"isoformat"):
        return x.isoformat()[:10]
    s=str(x)
    return s[:10]

assert EXECUTOR.is_file()
assert git_blob_sha(EXECUTOR)==EXECUTOR_BLOB
text=EXECUTOR.read_text(encoding="utf-8")
assert f'DATASET_REV = "{DATASET_REV}"' in text
assert f'DATASET_SHA256 = "{EXPECTED_SHA256}"' in text
assert f'DATASET_BYTES = {EXPECTED_BYTES}' in text
assert 'POPULATION = 200' in text
assert 'release < "2025-11-25"' in text

url=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{DATASET_REV}/data/test-00000-of-00001.parquet?download=true"
dst=pathlib.Path("frozen_livebench_if.parquet")
urllib.request.urlretrieve(url,dst)
raw=dst.read_bytes()
assert len(raw)==EXPECTED_BYTES,(len(raw),EXPECTED_BYTES)
assert hashlib.sha256(raw).hexdigest()==EXPECTED_SHA256

pf=pq.ParquetFile(dst)
md=pf.metadata
assert md.num_rows==EXPECTED_ROWS,(md.num_rows,EXPECTED_ROWS)
mins=[]; maxs=[]
found=0
for rg_i in range(md.num_row_groups):
    rg=md.row_group(rg_i)
    for c_i in range(rg.num_columns):
        col=rg.column(c_i)
        if col.path_in_schema=="livebench_release_date":
            found += 1
            st=col.statistics
            assert st is not None and st.has_min_max
            mins.append(norm_date(st.min))
            maxs.append(norm_date(st.max))
assert found>0
observed_min=min(mins)
observed_max=max(maxs)
assert observed_max==EXPECTED_MAX_RELEASE,(observed_max,EXPECTED_MAX_RELEASE)
assert observed_max < DISPATCH_BOUNDARY,(observed_max,DISPATCH_BOUNDARY)

print("LIVEBENCH_SCOPE_METADATA_ONLY_VERIFICATION=PASS")
print(f"dataset_sha256={EXPECTED_SHA256}")
print(f"dataset_rows={md.num_rows}")
print(f"release_date_min={observed_min}")
print(f"release_date_max={observed_max}")
print(f"dispatch_boundary={DISPATCH_BOUNDARY}")
print("decoded_prompt_rows=0")
print("decoded_kwargs_rows=0")
print("decoded_question_ids=0")
print("deduction=ALL_FROZEN_SELECTED_ROWS_DISPATCH_TO_LEGACY_IFEVAL")
print("modern_ifbench_types_on_frozen_critical_path=0")
print("legacy_registry_type_upper_bound=25")
