#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "executor":("subjects/public_source_federation_executor_v1.py","7e98588735d74fcdadfd9975e6043d2cacc42b70"),
 "compiler":("subjects/public_source_federation_v1.py","3f69b3e8371fe3e5abc173c6c9fe17e9003a938b"),
 "tests":("subjects/test_public_source_federation_executor_v1.py","2bfeb079808ec78dbadcd62f52bd12c5936b2812"),
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

executor=load("executor",FILES["executor"][0])
compiler=load("compiler",FILES["compiler"][0])

def fake_discover(query,limit=8,timeout=15,query_override=None):
 q=query_override or query
 if "gitlab.com" in q:
  return {
   "status":"CANDIDATES_DISCOVERED",
   "candidates":[
    {"url":"https://gitlab.com/acme/codec","title":"codec"},
    {"url":"https://github.com/wrong/host","title":"off-domain"},
   ],
   "retrieval_provenance":[{"backend":"FAKE","candidate_count":2}],
   "backend_errors":[],
  }
 if "gitee.com" in q:
  return {
   "status":"DISCOVERY_UNAVAILABLE",
   "candidates":[],
   "retrieval_provenance":[{"backend":"FAKE","candidate_count":0}],
   "backend_errors":[],
  }
 if "codeberg.org" in q:
  raise RuntimeError("temporary outage")
 return {
  "status":"CANDIDATES_DISCOVERED",
  "candidates":[{"url":"https://example.com/off-domain"}],
  "retrieval_provenance":[{"backend":"FAKE","candidate_count":1}],
  "backend_errors":[],
 }

fed=compiler.compile_federation(["UBJSON serializer"],max_queries_per_source=1)
assert fed["source_group_count"]==14,fed
out=executor.execute(fed,max_requests=2,discover_fn=fake_discover)
assert out["executed_request_count"]==2,out
assert out["candidate_count"]==1,out
assert out["candidates"][0]["federation_domain"]=="gitlab.com",out
assert out["candidates"][0]["sufficiency_status"]=="UNVERIFIED",out
assert out["nonexistence_claim_authorized"] is False,out
assert out["acceptance_credit"]==0,out

gitee=copy.deepcopy(fed)
gitee["requests"]=[x for x in gitee["requests"] if x["domain"]=="gitee.com"]
empty=executor.execute(gitee,discover_fn=fake_discover)
assert empty["cells"][0]["status"]=="QUERIED_NO_CANDIDATE",empty
assert len(empty["newly_consumed_request_ids"])==1,empty
assert empty["complete"] is False and empty["nonexistence_claim_authorized"] is False,empty

codeberg=copy.deepcopy(fed)
codeberg["requests"]=[x for x in codeberg["requests"] if x["domain"]=="codeberg.org"]
failed=executor.execute(codeberg,discover_fn=fake_discover)
assert failed["cells"][0]["status"]=="FAILED_TRANSIENT",failed
assert failed["cells"][0]["retryable"] is True,failed
assert failed["newly_consumed_request_ids"]==[],failed

first=executor.execute(fed,max_requests=1,discover_fn=fake_discover)
second=executor.execute(
 fed,
 consumed_request_ids=first["consumed_request_ids_after"],
 max_requests=1,
 discover_fn=fake_discover,
)
assert second["skipped_consumed_request_count"]>=1,second
assert set(first["newly_consumed_request_ids"]).isdisjoint(second["newly_consumed_request_ids"]),second

badfed=copy.deepcopy(fed)
badfed["requests"]=[x for x in badfed["requests"] if x["domain"]=="gitlab.com"]
def bad(query,limit=8,timeout=15,query_override=None):
 return {
  "status":"CANDIDATES_DISCOVERED",
  "candidates":[{"url":"https://gitlab.com/acme/codec","verified_sufficient":True}],
  "retrieval_provenance":[{"backend":"BAD"}],
  "backend_errors":[],
 }
badout=executor.execute(badfed,discover_fn=bad)
assert badout["cells"][0]["status"]=="FAILED_TRANSIENT",badout
assert badout["candidate_count"]==0 and badout["acceptance_credit"]==0,badout

a=executor.execute(fed,max_requests=3,discover_fn=fake_discover)
b=executor.execute(copy.deepcopy(fed),max_requests=3,discover_fn=fake_discover)
assert a["source_epoch_sha256"]==b["source_epoch_sha256"],(a,b)

print("PUBLIC_SOURCE_FEDERATION_EXECUTOR_V1_VERIFIED")
print(json.dumps({
 "exact_blobs":{k:v[1] for k,v in FILES.items()},
 "source_group_count":fed["source_group_count"],
 "actual_execution":True,
 "off_domain_filter":True,
 "empty_result_nonexistence_firewall":True,
 "transient_failure_retryable":True,
 "consumed_cell_replay_disabled":True,
 "candidate_self_promotion_blocked":True,
 "deterministic_epoch_receipt":True,
 "zero_credit":True,
},sort_keys=True))
