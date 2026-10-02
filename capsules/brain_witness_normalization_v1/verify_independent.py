from __future__ import annotations
import hashlib, json
from pathlib import Path
from canonical.runtime.brain_witness_normalization_verifier_v1 import evaluate, git_blob_sha

ROOT=Path(__file__).resolve().parent
SOURCE="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
NORMALIZED="canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def blob(rel):
    b=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

source=load(SOURCE)
normalized=load(NORMALIZED)
out=evaluate(source,normalized,blob(SOURCE))
assert out["status"]=="PASS__EXACT_CONTENT_ADDRESSED_WITNESS_NORMALIZATION__ZERO_SEMANTIC_CREDIT",out
assert out["witness_count"]==9,out
assert out["semantic_implication_verified"] is False,out
assert normalized["authority"]["evidence_bindings"]["git_blob_sha"]==blob(SOURCE)
assert all(w["normalized_target_atoms"]==[] for w in normalized["witnesses"])
assert all(w["semantic_implications"]==[] for w in normalized["witnesses"])
assert out["acceptance_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["new_reality_units_consumed"]==0
print(json.dumps(out,indent=2,sort_keys=True))
