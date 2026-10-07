import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAND=ROOT/"candidate.json"
EXPECTED_BLOB="55a027d50e6f9d1c4d70a75b39d6a536e26a4277"

raw=CAND.read_bytes()
git_blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
assert git_blob==EXPECTED_BLOB, (git_blob, EXPECTED_BLOB)

j=json.loads(raw)
assert j["schema"]=="PROJECT_BRAIN_TARGET_SUPERSET_COVERAGE_DOMINANCE_NORMAL_FORM_V1"
assert j["theorem"]["exact_enumeration_not_necessary"] is True
assert j["theorem"]["exact_domain_equality_not_necessary"] is True
assert set(j["theorem"]["sufficient_conditions"])=={
    "PROVE_U_SUBSET_OR_EQUAL_D",
    "PROVE_BRAIN_DOMINATES_OPUS55_OVER_EVERY_LOAD_BEARING_CELL_IN_D",
}
assert j["current_verdict"]["literal_terminal_finality"] is False
assert j["current_verdict"]["acceptance_credit_delta"]==0
assert j["accounting"]["new_reality_units_consumed"]==0
assert j["execution_authority"] is False
assert j["promotion_authority"] is False
assert j["fresh_reality_authority"] is False

# Recompute the core set-theoretic implication on multiple finite witnesses.
def certifies(U,D,dominates_D):
    coverage=set(U) <= set(D)
    return coverage and all(dominates_D.get(x,False) for x in D)

U={"u1","u2"}
D={"u1","u2","extra"}
dom={x:True for x in D}
assert certifies(U,D,dom) is True

# Equality U=D is not required.
assert U != D

# Missing coverage must fail closed even if every element of D is dominated.
U2={"u1","hidden"}
D2={"u1","extra"}
dom2={x:True for x in D2}
assert certifies(U2,D2,dom2) is False

# Coverage alone is insufficient when a covered cell lacks dominance.
dom3={"u1":True,"u2":False,"extra":True}
assert certifies(U,D,dom3) is False

# W3 cannot omit an explicit coverage premise under the candidate normal form.
consequences=j["witness_class_reduction"]["consequences"]
assert any("W3_IS_NOT_A_WAY_TO_AVOID_TARGET_COMPLETENESS_INFORMATION" in x for x in consequences)

print(json.dumps({
    "status":"PASS",
    "verified_private_git_blob_sha":git_blob,
    "core_implication":"U_SUBSET_D_AND_DOMINANCE_D_IMPLIES_DOMINANCE_U",
    "exact_equality_required":False,
    "coverage_omission_negative_canary":True,
    "dominance_omission_negative_canary":True,
    "acceptance_credit_delta":0,
    "fresh_reality_authority":False
},sort_keys=True))
