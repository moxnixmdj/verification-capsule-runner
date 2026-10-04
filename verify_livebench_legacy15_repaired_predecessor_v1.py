#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, importlib, json, pathlib, sys, urllib.request
import pyarrow.parquet as pq
from canonical.runtime import livebench_frozen_active_legacy15_v1 as active15
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime import livebench_legacy15_joint_witness_v1 as witness

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
 "canonical/runtime/livebench_legacy15_joint_witness_v1.py":"e767bb2180a1e753ebb7b5ad61029ace754b6f0b",
}

def git_blob_bytes(raw:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for path,sha in BRAIN_BLOBS.items():
 got=git_blob_bytes(pathlib.Path(path).read_bytes())
 assert got==sha,(path,got,sha)

active_digest=hashlib.sha256(json.dumps(sorted(active15.ACTIVE_IDS)).encode()).hexdigest()
assert active_digest=="af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

pkgroot=pathlib.Path("exact_livebench"); pkg=pkgroot/"instruction_following_eval"
pkg.mkdir(parents=True,exist_ok=True); (pkg/"__init__.py").write_text("")
for name,sha in SOURCE_FILES.items():
 url=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LB_COMMIT}/livebench/if_runner/instruction_following_eval/{name}"
 raw=urllib.request.urlopen(url,timeout=30).read()
 assert git_blob_bytes(raw)==sha,(name,git_blob_bytes(raw),sha)
 (pkg/name).write_bytes(raw)
sys.path.insert(0,str(pkgroot.resolve()))
registry=importlib.import_module("instruction_following_eval.instructions_registry")

url=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{REV}/data/test-00000-of-00001.parquet?download=true"
dst=pathlib.Path("predecessor.parquet"); urllib.request.urlretrieve(url,dst)
raw=dst.read_bytes(); assert len(raw)==DATA_BYTES; assert hashlib.sha256(raw).hexdigest()==DATA_SHA256
rows=pq.read_table(dst).to_pylist(); assert len(rows)==ROWS

active=set(active15.ACTIVE_IDS); eligible=solved=compile_fail=runtime_fail=checker_fail=0
fail_ids=collections.Counter(); fail_shapes=collections.Counter(); samples=[]

def check_candidate(prompt,ids,kwargs,response):
 per=[]
 for pos,iid in enumerate(ids):
  inst=registry.INSTRUCTION_DICT[iid](iid)
  kw={str(k):v for k,v in dict(kwargs[pos] or {}).items() if v is not None}
  inst.build_description(**kw)
  args=inst.get_instruction_args()
  if args and "prompt" in args: inst.build_description(prompt=prompt)
  ok=bool(response.strip()) and bool(inst.check_following(response))
  per.append((iid,ok))
 return all(x[1] for x in per),per

for idx,row in enumerate(rows):
 ids=[str(x) for x in (row.get("instruction_id_list") or [])]
 if not ids or not set(ids).issubset(active): continue
 eligible+=1
 prompt=str(list(row.get("turns") or [])[0]); kwargs=list(row.get("kwargs") or [])
 compiled=compiler.compile_visible_constraints(prompt)
 got=[str(c.get("instruction_id")) for c in (compiled.get("constraints") or [])]
 if compiled.get("status")!="PASS" or collections.Counter(got)!=collections.Counter(ids):
  compile_fail+=1
  if len(samples)<30:samples.append({"row":idx,"kind":"compile","ids":ids,"got":got,"status":compiled.get("status")})
  continue
 out=witness.solve(prompt)
 if out.get("status")!="PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
  runtime_fail+=1
  if len(samples)<30:samples.append({"row":idx,"kind":"runtime","ids":ids,"error":out.get("error"),"status":out.get("status")})
  continue
 ok,checks=check_candidate(prompt,ids,kwargs,str(out["response"]))
 if ok: solved+=1
 else:
  checker_fail+=1; fail_shapes[tuple(sorted(ids))]+=1
  for iid,pass_ in checks:
   if not pass_: fail_ids[iid]+=1
  if len(samples)<30:samples.append({"row":idx,"kind":"checker","ids":ids,"checks":checks})

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY15_REPAIRED_PREDECESSOR_V1",
 "status":"PASS__ALL_ELIGIBLE_PREDECESSOR_ROWS_EXACT_FULL_SCORE" if solved==eligible else "FAIL_CLOSED__REPAIR_LEDGER",
 "bindings":{"predecessor_revision":REV,"predecessor_sha256":DATA_SHA256,"livebench_commit":LB_COMMIT,"active15_commitment":active_digest,**BRAIN_BLOBS},
 "scope":{"predecessor_rows_read":200,"eligible_active15_rows":eligible,"active_terminal_rows_read":0,"active_terminal_prompt_text_read":False},
 "results":{"solved_rows":solved,"compile_fail_rows":compile_fail,"runtime_fail_rows":runtime_fail,"checker_fail_rows":checker_fail},
 "failed_instruction_ids":dict(fail_ids),
 "failed_shapes":[{"ids":list(k),"count":v} for k,v in fail_shapes.most_common()],
 "failure_samples":samples,
 "accounting":{"incremental_spend_usd":0,"terminal_cases_consumed":0},
}
pathlib.Path("receipts").mkdir(exist_ok=True)
pathlib.Path("receipts/livebench_legacy15_repaired_predecessor_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":receipt["status"],**receipt["scope"],**receipt["results"]},sort_keys=True))
if samples: print("FAILURE_SAMPLES="+json.dumps(samples,ensure_ascii=False,sort_keys=True))
assert compile_fail==0,compile_fail
assert runtime_fail==0,runtime_fail
assert checker_fail==0,checker_fail
assert solved==eligible,(solved,eligible)
