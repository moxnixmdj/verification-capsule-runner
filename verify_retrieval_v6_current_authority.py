#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
P=R/"subjects/canonical__governance__RETRIEVAL_CURRENT_AUTHORITY_V1.json"
A=R/"subjects/v6current_RETRIEVAL_V6_OPEN_WORLD_HARDENING_ACTIVATION_V1.json"
V=R/"subjects/v6current_RETRIEVAL_V6_OPEN_WORLD_HARDENING_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
assert blob(P)=="46b2fc41854b68b0c994504443c9c3d361773c40",blob(P)
assert blob(A)=="4398fee2d6d0a8a62ca7209852c961bc1fca1c7c",blob(A)
assert blob(V)=="5bb0556c0e1c810bb6d7594e039667e03d8309ec",blob(V)
p=json.loads(P.read_text());a=json.loads(A.read_text());v=json.loads(V.read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V6_OPEN_WORLD_HARDENING_OVER_V5__ZERO_CREDIT"
assert p["authority"]["git_blob_sha"]==blob(A)
assert p["independent_verification"]["git_blob_sha"]==blob(V)
assert p["independent_verification"]["conclusion"]=="success"
assert p["measured_declared_fixture_results"]["generated_cases"]==291
assert p["measured_declared_fixture_results"]["v6_finite_fixture_recall"]==1.0
assert p["measured_declared_fixture_results"]["lexical_only_recall"]<1.0
for rule in ("NO_RERANKER_MAY_DELETE_AN_OBSERVED_CANDIDATE","USE_QUERYLESS_ENUMERATION_WHEN_A_FINITE_ENUMERABLE_SCOPE_EXISTS","ZERO_YIELD_ROUNDS_NEVER_AUTHORIZE_COMPLETENESS","OPEN_WORLD_NO_RESULT_REMAINS_UNKNOWN"):
 assert rule in p["hard_rules"],rule
assert v["independent_runner"]["conclusion"]=="success"
assert v["verified"]["pairwise_failure_dimension_coverage"] is True
assert v["verified"]["open_world_completeness_claim_authorized"] is False
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("RETRIEVAL_V6_CURRENT_AUTHORITY_VERIFIED")
