#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
P=R/"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json"
V=R/"canonical/verification/GLOBAL_RETRIEVAL_V7_MECHANICAL_ENTRYPOINT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
assert blob(P)=="6a556eb0689e1a122730d46ef37f8d4b272714a2",blob(P)
assert blob(V)=="3573f2771ae9a7e2b805c66db277448265066fd4",blob(V)
p=json.loads(P.read_text());v=json.loads(V.read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__MECHANICAL_ENTRYPOINT_V1_BOUND__ZERO_CREDIT"
m=p["mechanical_entrypoint"]
assert m["authority_guard_git_blob_sha"]=="7b4cfd559d68c272f241cd2a6354dcf22f1b6957"
assert m["entrypoint_git_blob_sha"]=="c206fa36942fd178953434e80ad7ccf51f815e09"
assert m["verification_git_blob_sha"]=="3573f2771ae9a7e2b805c66db277448265066fd4"
assert m["conclusion"]=="success"
assert m["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert v["independent_runner"]["conclusion"]=="success"
assert "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_PASS_THE_FAIL_CLOSED_CURRENT_AUTHORITY_GUARD" in p["hard_rules"]
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V7_CURRENT_POINTER_INTEGRATION_VERIFIED")
