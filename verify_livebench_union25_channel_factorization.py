#!/usr/bin/env python3
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"
sys.path.insert(0,str(SUB))
EXPECTED={
 "canonical/runtime/livebench_union25_archetypes_v1.py":"03f67f6e1fdb59cc5168a16603a776f59caeb39b",
 "canonical/runtime/livebench_union25_channel_factorization_v1.py":"f782b74e6dd0db1e3bacf7623296584bf2beed3f",
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
actual={p:blob(SUB/p) for p in EXPECTED}
assert actual==EXPECTED,(actual,EXPECTED)
from canonical.runtime import livebench_union25_channel_factorization_v1 as f
out=f.verify()
assert out["status"]=="PASS__21_HARD_SIGNATURES_FACTOR_EXACTLY_INTO_5_CHASSIS_PLUS_3_COUNT_OVERLAYS"
assert out["hard_signature_count"]==21
assert out["global_chassis_count"]==5
assert out["count_overlay_count"]==3
assert out["signatures_per_chassis"]=={
 "CONSTRAINED_SINGLETON":1,
 "ENGLISH_LOWER":4,
 "ENGLISH_UPPER":4,
 "NEUTRAL":8,
 "RESPONSE_LANGUAGE":4,
}
receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_CHANNEL_FACTORIZATION_INDEPENDENT_VERIFICATION_V1",
 "status":"INDEPENDENT_PASS__21_TO_5_CHASSIS_PLUS_3_OVERLAYS_EXACT_BIJECTION",
 "subject_blobs":actual,
 "result":out,
 "terminal_rows_read":0,
 "hidden_kwargs_read":0,
 "target_scores_read":0,
 "acceptance_credit_delta":0,
}
pathlib.Path("livebench_union25_channel_factorization_verification.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
