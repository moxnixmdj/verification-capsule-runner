from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"isolated/unknown-domain-execution-lease-v2"

EXPECTED_BLOBS={
 "brain_runtime.py":"61487ed479e08c3f9f2cd19977e7fe7d2ca0230e",
 "brain_tests.py":"1bb1a6d9fd09dbc3a4673ffeb372bc4b7d57239b",
 "brain_candidate.json":"8a360a230e956f79507f40fdde8725a401c4a6ae",
 "generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
}
EXPECTED_DIGEST="7e23ef76fd83b58374db8ddfe87c82d109235559a44c9715ca16824f7b43d731"

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for rel,expected in EXPECTED_BLOBS.items():
    p=SUB/rel
    assert p.is_file(), rel
    got=git_blob(p.read_bytes())
    assert got==expected,(rel,got,expected)

spec=importlib.util.spec_from_file_location("udlease_repaired",SUB/"brain_runtime.py")
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

candidate=json.loads((SUB/"brain_candidate.json").read_text())
assert candidate["subjects"]["runtime_git_blob_sha"]==EXPECTED_BLOBS["brain_runtime.py"]
assert candidate["subjects"]["tests_git_blob_sha"]==EXPECTED_BLOBS["brain_tests.py"]
assert candidate["subjects"]["generator_v1_git_blob_sha"]==EXPECTED_BLOBS["generator_v1.py"]
assert "TRANSITIVE_DEPENDENCY_CLOSED" in candidate["status"]

payload=mod.canonical_lease_payload()
digest=mod.lease_digest_sha256(payload)
assert digest==EXPECTED_DIGEST,(digest,EXPECTED_DIGEST)
assert mod.expected_claim_ref(payload)=="refs/heads/unknown-domain-direct-claims/"+EXPECTED_DIGEST
assert payload["exact_execution_subject"]["generator_v1"]==EXPECTED_BLOBS["generator_v1.py"]

raw=json.dumps(payload,sort_keys=True)
for forbidden in ("nonce","timestamp","run_label"):
    assert forbidden not in raw.lower()

state={
 "target_predicate":mod.TARGET,
 "authorized_leaves":list(mod.AUTHORIZED_LEAVES),
 "activation_git_blob_sha":mod.ACTIVATION_BLOB,
 "qualification_receipt_git_blob_sha":mod.QUALIFICATION_RECEIPT_BLOB,
 "production_precommit_git_blob_sha":mod.PRODUCTION_PRECOMMIT_BLOB,
 "exact_execution_subject":dict(mod.EXACT_SUBJECTS),
 "qualification_independent_pass":True,
 "activation_independent_pass":True,
 "exact_subject_blobs_rechecked":True,
 "production_cases_consumed":0,
 "production_populations_generated":0,
 "persistent_learned_bytes":0,
 "external_frontier_model_calls":0,
 "external_learned_capability_calls":0,
 "incremental_spend_usd":0,
 "production_beacon_generated":False,
 "candidate_mutated_after_qualification":False,
 "global_fresh_reality":False,
 "execution_started":False,
}
out=mod.verify_point_of_use_state(state)
assert out["ready_for_atomic_claim_only"] is True,out
assert out["lease_digest_sha256"]==EXPECTED_DIGEST
assert out["claim_ref"]=="refs/heads/unknown-domain-direct-claims/"+EXPECTED_DIGEST
assert out["case_generation_authority"] is False
assert out["execution_authority"] is False

for field,value in (
    ("production_cases_consumed",1),
    ("production_populations_generated",1),
    ("persistent_learned_bytes",1),
    ("external_frontier_model_calls",1),
    ("external_learned_capability_calls",1),
    ("incremental_spend_usd",1),
):
    bad=copy.deepcopy(state); bad[field]=value
    assert mod.verify_point_of_use_state(bad)["ready_for_atomic_claim_only"] is False,field

bad=copy.deepcopy(state)
bad["exact_execution_subject"]["generator_v1"]="0"*40
bad_out=mod.verify_point_of_use_state(bad)
assert bad_out["ready_for_atomic_claim_only"] is False
assert mod.lease_digest_sha256({
    **payload,
    "exact_execution_subject":{**payload["exact_execution_subject"],"generator_v1":"0"*40},
}) != EXPECTED_DIGEST

print(json.dumps({
 "status":"INDEPENDENT_REPAIRED_EXECUTION_LEASE_PASS",
 "execution_lease_sha256":EXPECTED_DIGEST,
 "claim_ref":"refs/heads/unknown-domain-direct-claims/"+EXPECTED_DIGEST,
 "exact_subject_count":len(payload["exact_execution_subject"]),
 "generator_v1_bound":True,
 "persistent_learned_bytes":0,
 "production_cases_consumed":0
},sort_keys=True))
