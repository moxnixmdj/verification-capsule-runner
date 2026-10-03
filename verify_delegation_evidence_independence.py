#!/usr/bin/env python3
import copy, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
S=ROOT/"subjects/delegation_evidence_independence"
EXPECTED={
 "base_evidence":"f99b00e6dca735ffa7a790a414155b4f69856cf0",
 "candidate_evidence":"bc420c6d1a6caaab7a6d5c257640d3f5797170f5",
 "acceptance_receipt":"d04f2a8c5594d261158835db1cae3822411b6b23",
 "scope_receipt":"955ac8f4bd0db2527bfbb465fc8252df6d916156",
}
FILES={k:S/(k+".json") for k in EXPECTED}
TARGET="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(k):
    return json.loads(FILES[k].read_text(encoding="utf-8"))
for k,p in FILES.items():
    assert blob(p)==EXPECTED[k],(k,blob(p),EXPECTED[k])

base=load("base_evidence")
cand=load("candidate_evidence")
acc=load("acceptance_receipt")
scope=load("scope_receipt")

assert str(acc["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert acc["public_runner"]["conclusion"]=="success"
assert TARGET in acc["promotion_scope"]
assert acc["verified_result"]["scope_completeness_basis"]=="UNIVERSAL_FORMAL_SCOPE_PROOF"

assert str(scope["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert scope["public_runner"]["conclusion"]=="success"
assert scope["target_predicate"]==TARGET
assert "UNIVERSAL_SCOPE_PROVED_TRUE" in scope["verified"]
assert "BASIS_KIND_UNIVERSAL_FORMAL_SCOPE_PROOF" in scope["verified"]

brow=next(x for x in base["claims"] if x.get("predicate_id")==TARGET)
crow=next(x for x in cand["claims"] if x.get("predicate_id")==TARGET)
assert brow.get("independent_or_objective") is None
assert crow["independent_or_objective"] is True
assert crow["source_sha"]==EXPECTED["acceptance_receipt"]
assert crow["scope_completeness"]["receipt_sha"]==EXPECTED["scope_receipt"]
assert crow["state"]=="PROVED"
assert crow["scope_complete"] is True
assert crow["objective_ceiling"] is True
assert crow["proof_kind"]=="ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"

basis=crow["independence_basis"]
assert basis["source_receipt_sha"]==EXPECTED["acceptance_receipt"]
assert basis["universal_scope_receipt_sha"]==EXPECTED["scope_receipt"]
assert basis["source_receipt_status"]==acc["status"]
assert basis["universal_scope_receipt_status"]==scope["status"]

# Candidate must differ from base only by the two explicit metadata additions on TARGET.
expected=copy.deepcopy(base)
erow=next(x for x in expected["claims"] if x.get("predicate_id")==TARGET)
erow["independent_or_objective"]=True
erow["independence_basis"]=basis
assert cand==expected

# Counts and every non-target claim are byte-semantically unchanged after JSON parse.
def proved(doc):
    return [x for x in doc["claims"] if x.get("state")=="PROVED"]
assert len(proved(base))==len(proved(cand))==12
assert len(base["claims"])==len(cand["claims"])
for b,c in zip(base["claims"],cand["claims"]):
    if b.get("predicate_id")!=TARGET:
        assert b==c

print("DELEGATION_EVIDENCE_INDEPENDENCE_METADATA_INDEPENDENT_VERIFIED")
