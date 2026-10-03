#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
P=R/"subjects/v13_current_pointer_final.json"
V=R/"subjects/v13_pointer_candidate_verification_final.json"
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
assert blob(P)=="6717ff6bda388722b3a28f0ead66db7aadb8e0c7",blob(P)
assert blob(V)=="4da56ab4f42e56ae1f4046c7e66ac7483eeeff39",blob(V)
p=json.loads(P.read_text());v=json.loads(V.read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V13_CURRENT__RETRIEVAL_V5_MANDATORY__ZERO_CREDIT"
assert p["current_authority"]["git_blob_sha"]=="9fb9897d55641aaa54d82a5740c51970e677acb0"
assert p["independent_verification"]["git_blob_sha"]=="e86a86a251fee63876a387a50060d88a4d26ec0e"
assert p["final_pointer_candidate_verification"]["git_blob_sha"]=="4da56ab4f42e56ae1f4046c7e66ac7483eeeff39"
assert p["final_pointer_candidate_verification"]["conclusion"]=="success"
assert v["independent_runner"]["conclusion"]=="success"
m=p["mandatory_tool_discovery_retrieval"]
assert m["authority"]=="V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_BASE"
assert m["gate_git_blob_sha"]=="c3324e574c1fafb6aaab443f49b7a9600966e754"
assert m["mandatory"] is True
assert m["direct_bypass_allowed"] is False
assert m["stale_v3_or_v4_only_authority_allowed"] is False
assert m["failed_or_partial_source_cell_consumes_epoch"] is False
assert m["consumed_source_epoch_replay_allowed"] is False
assert m["no_result_means_nonexistence"] is False
assert p["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert p["live_world"]["primitive_zero_reality_work_units"]==31
assert p["execution_authority"] is False and p["promotion_authority"] is False and p["fresh_reality_authority"] is False
print("TERMINAL_SCHEDULING_V13_CURRENT_POINTER_FINAL_VERIFIED")
