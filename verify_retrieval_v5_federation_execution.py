#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "federation":("subjects/public_source_federation_v2.py","32f0443bfb1859168e14f7266a3b5b3c99a40f45"),
 "executor":("subjects/public_source_federation_executor_v2.py","96497b15a9c096b8e5cc471313ae165fceaedd07"),
 "tests":("subjects/test_retrieval_v5_federation_execution.py","cf60eb77afa85604e56870d0a0458d7c1571c0f6"),
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for k,(p,s) in FILES.items():
 got=blob(ROOT/p)
 assert got==s,(k,got,s)

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path)
 mod=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(mod)
 return mod

fedmod=load("fedmod",FILES["federation"][0])
executor=load("executor",FILES["executor"][0])

queries=[
 {"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"},
 {"text":"工具发现 Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
 {"text":"اكتشاف الأدوات Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
 {"text":"обнаружение инструментов Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
]

def ok(query,limit=8,timeout=15,query_override=None):
 q=query_override or query
 domain=q.split()[0].removeprefix("site:")
 return {
  "status":"CANDIDATES_DISCOVERED",
  "candidates":[
   {"url":f"https://{domain}/candidate","title":"candidate"},
   {"url":"https://wrong.example/off-domain","title":"wrong"},
  ],
  "retrieval_provenance":[{"backend":"FAKE","candidate_count":2}],
  "backend_errors":[],
 }

fed=fedmod.compile_federation(queries,max_queries_per_source=1)
assert fed["source_group_count"]==14,fed

partial=executor.execute(fed,max_requests=3,discover_fn=ok)
assert partial["epoch_consumption_authorized"] is False,partial
assert len(partial["consumed_request_ids_after"])==3,partial
assert len(partial["remaining_request_ids"])==fed["request_count"]-3,partial

full=executor.execute(fed,max_requests=64,discover_fn=ok)
assert full["epoch_consumption_authorized"] is True,full
assert full["remaining_request_ids"]==[],full
assert full["complete"] is False,full
assert full["nonexistence_claim_authorized"] is False,full
assert full["candidate_count"]==14,full

target=fed["requests"][0]["domain"]
def flaky(query,limit=8,timeout=15,query_override=None):
 q=query_override or query
 if f"site:{target}" in q:
  raise RuntimeError("temporary outage")
 return ok(query,limit,timeout,query_override)

failed=executor.execute(fed,max_requests=64,discover_fn=flaky)
assert failed["epoch_consumption_authorized"] is False,failed
assert len(failed["failed_retryable_request_ids"])==1,failed
rid=fed["requests"][0]["request_id"]
assert rid in failed["remaining_request_ids"],failed
cell=next(x for x in failed["cells"] if x["request_id"]==rid)
assert cell["consumed"] is False and cell["retryable"] is True,cell

one=executor.execute(fed,max_requests=1,discover_fn=ok)
assert one["candidate_count"]==1,one
assert one["candidates"][0]["federation_domain"]==fed["requests"][0]["domain"],one

first=executor.execute(fed,max_requests=2,discover_fn=ok)
second=executor.execute(
 fed,consumed_request_ids=first["consumed_request_ids_after"],max_requests=2,discover_fn=ok
)
assert second["skipped_consumed_request_count"]>=2,second
assert set(first["newly_consumed_request_ids"]).isdisjoint(second["newly_consumed_request_ids"]),second

tampered=copy.deepcopy(fed)
tampered["requests"][0]["request_id"]="0"*24
try:
 executor.execute(tampered,discover_fn=ok)
 raise AssertionError("tampered request id accepted")
except executor.FederationExecutionError:
 pass

onefed=copy.deepcopy(fed)
onefed["requests"]=onefed["requests"][:1]
def smuggle(query,limit=8,timeout=15,query_override=None):
 domain=(query_override or query).split()[0].removeprefix("site:")
 return {
  "status":"CANDIDATES_DISCOVERED",
  "candidates":[{"url":f"https://{domain}/x","verified_sufficient":True}],
  "retrieval_provenance":[{"backend":"BAD"}],
  "backend_errors":[],
 }
bad=executor.execute(onefed,discover_fn=smuggle)
assert bad["epoch_consumption_authorized"] is False,bad
assert bad["newly_consumed_request_ids"]==[],bad
assert len(bad["failed_retryable_request_ids"])==1,bad
assert bad["acceptance_credit"]==0,bad

a=executor.execute(fed,max_requests=5,discover_fn=ok)
b=executor.execute(copy.deepcopy(fed),max_requests=5,discover_fn=ok)
assert a["source_epoch_sha256"]==b["source_epoch_sha256"],(a,b)

print("RETRIEVAL_V5_FEDERATION_EXECUTION_VERIFIED")
print(json.dumps({
 "exact_blobs":{k:v[1] for k,v in FILES.items()},
 "source_group_count":fed["source_group_count"],
 "partial_batch_cannot_consume_epoch":True,
 "transient_failure_unconsumed_and_retryable":True,
 "all_selected_cells_required_for_epoch_consumption":True,
 "off_domain_filtering":True,
 "replay_suppression":True,
 "request_id_tamper_rejected":True,
 "candidate_self_promotion_rejected":True,
 "deterministic_epoch_receipt":True,
 "epoch_consumption_does_not_authorize_nonexistence":True,
 "zero_credit":True
},sort_keys=True))
