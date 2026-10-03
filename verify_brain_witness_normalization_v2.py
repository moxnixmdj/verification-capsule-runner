#!/usr/bin/env python3
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
S=ROOT/"subjects/brain_witness_normalization_v2"
EXPECTED={
 "normalized":"fc64c7a9812363b7ed2473c98a89f6a7dc6b688d",
 "runtime":"aae29ea761442ba6d51a8218261e88c32e091bb1",
 "test":"aaabc6e55ba87e663ae600b1009a9bca05c486b0",
 "evidence":"f99b00e6dca735ffa7a790a414155b4f69856cf0",
}
FILES={k:S/(k+(".py" if k in {"runtime","test"} else ".json")) for k in EXPECTED}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,p in FILES.items(): assert blob(p)==EXPECTED[k],(k,blob(p),EXPECTED[k])
spec=importlib.util.spec_from_file_location("norm",FILES["runtime"]); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
source=json.loads(FILES["evidence"].read_text()); normalized=json.loads(FILES["normalized"].read_text())
out=mod.evaluate(source,normalized,EXPECTED["evidence"])
assert out["pass"] is True,out
assert out["witness_count"]==12,out
assert out["semantic_implication_verified"] is False
assert out["scope_relation_verified"] is False
assert out["acceptance_credit_delta"]==0 and out["family_credit_delta"]==0 and out["ownership_credit_delta"]==0
actual_ids=[x["source_predicate_id"] for x in normalized["witnesses"]]
expected_ids=[x["predicate_id"] for x in source["claims"] if x.get("state")=="PROVED"]
assert actual_ids==expected_ids
assert all(x["normalized_target_atoms"]==[] and x["semantic_implications"]==[] for x in normalized["witnesses"])
bad=json.loads(json.dumps(normalized)); bad["witnesses"][0]["semantic_implications"]=["invented"]
fail=mod.evaluate(source,bad,EXPECTED["evidence"])
assert fail["pass"] is False
assert any("SEMANTIC_IMPLICATION_CREDIT_FORBIDDEN" in e for e in fail["errors"])
missing=json.loads(json.dumps(normalized)); missing["witnesses"]=missing["witnesses"][:-1]; missing["witness_count"]-=1
fail2=mod.evaluate(source,missing,EXPECTED["evidence"])
assert fail2["pass"] is False
print("BRAIN_WITNESS_NORMALIZATION_V2_INDEPENDENT_VERIFIED")
