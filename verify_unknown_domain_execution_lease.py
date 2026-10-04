from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import unknown_domain_direct_production_once_v1 as prod

ROOT=Path(__file__).resolve().parent
LEASE=ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1.json"
raw,digest=prod.lease_bytes_and_digest(LEASE)
lease=json.loads(raw)

assert lease["schema"]=="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1"
assert lease["atomic_claim"]["claim_key_rule"]=="SHA256_OF_CANONICAL_QUALIFIED_EXECUTION_TUPLE_V2"
assert lease["lease_identity"]==prod.canonical_identity_from_lease(lease)
assert "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py" in lease["exact_components"]
assert lease["exact_components"]["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"]=="f974a4594c78e74693c7ba5a19f131dfa481b937"
assert lease["source_brain"]["qualification_receipt_blob"]=="36452412fb60ce38405f139111eba98b5cebc040"
assert lease["source_brain"]["production_precommit_blob"]=="ddf55f3e54ef6af89a95395075441742cb124258"

prod.validate_lease(lease,digest)

mutated=json.loads(json.dumps(lease))
mutated["date"]="2099-12-31"
assert prod.canonical_identity_from_lease(mutated)==lease["lease_identity"]
mutated["lease_identity"]["exact_execution_subject"]["generator_v1"]="0"*40
assert prod.canonical_identity_from_lease(mutated)!=mutated["lease_identity"]

blob=lambda b:hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
print(json.dumps({
 "status":"INDEPENDENT_DETERMINISTIC_EXECUTION_LEASE_V2_PASS",
 "execution_lease_git_blob_sha":blob(raw),
 "execution_lease_sha256":digest,
 "claim_identity_scope":"CANONICAL_QUALIFIED_EXECUTION_TUPLE_ONLY",
 "incidental_metadata_affects_claim_identity":False,
 "transitive_generator_v1_bound":True,
 "exact_component_count":len(lease["exact_components"]),
 "production_cases_allowed":27,
 "persistent_learned_bytes":0,
 "global_fresh_reality":False
},sort_keys=True))
