from __future__ import annotations
import hashlib, json
from pathlib import Path

BASE=Path("capsules/arena-public-semantics-truth-repair-active-v1")
FILES={
 "ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json":"a76391c98767a0fa688adc32f5ac23f9caaea624",
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":"54021118b1b1f299cf0191d1e413a3009d95d76c",
 "CURRENT_TERMINAL_AUTHORITY_V1.json":"09c8686990eceb6dee49229390f30e3b3b2e83de",
}
def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load(name:str)->dict:
    p=BASE/name
    data=p.read_bytes()
    assert blob_sha(data)==FILES[name], (name,blob_sha(data),FILES[name])
    return json.loads(data)

def main()->dict:
    repair=load("ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json")
    root=load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
    current=load("CURRENT_TERMINAL_AUTHORITY_V1.json")

    assert repair["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__TRUTH_REPAIR__SCHEDULING_ONLY__ZERO_CREDIT"
    assert repair["scheduling_authority"] is True
    assert repair["execution_authority"] is False
    assert repair["promotion_authority"] is False
    assert repair["fresh_reality_authority"] is False
    assert repair["independent_verification_required"] is False
    v=repair["verification"]
    assert v["runner_pull_request"]==1785
    assert v["runner_merge_commit"]=="75fc0cb31f613c3d5b8a242d763135966e6a5a53"
    assert v["workflow_run_id"]==37190832565
    assert v["conclusion"]=="success"

    assert repair["observed_now"]["authenticated_api_portal_existence_publicly_reproducible"] is True
    assert repair["observed_now"]["endpoint_and_routing_semantics_unauthenticated_publicly_reproducible"] is False

    for ptr in (
      root["scheduler_policy"]["arena_public_semantics_truth_repair"],
      current["arena_public_semantics_truth_repair"],
    ):
        assert ptr["path"]=="canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json"
        assert ptr["git_blob_sha"]=="a76391c98767a0fa688adc32f5ac23f9caaea624"
        assert ptr["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__TRUTH_REPAIR__ZERO_CREDIT"
        assert ptr["verification_runner_pr"]==1785
        assert ptr["verification_workflow_run_id"]==37190832565
        assert ptr["scheduling_authority"] is True
        assert ptr["execution_authority"] is False
        assert ptr["promotion_authority"] is False
        assert ptr["fresh_reality_authority"] is False

    ca=root["current_acceptance"]
    assert (ca["accepted_families"],ca["proved_atomic"],ca["unresolved_atomic"],ca["terminal"])==(5,12,26,False)
    assert repair["accounting"]["acceptance_credit_delta"]==0

    return {
      "schema":"PROJECT_BRAIN_ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_ACTIVE_PROJECTION_CAPSULE_V1",
      "status":"PASS",
      "exact_blob_identity":True,
      "active_projection_verified":True,
      "terminal_counts_preserved":True,
      "acceptance_credit_delta":0,
      "fresh_reality_authority":False
    }

if __name__=="__main__":
    print(json.dumps(main(),sort_keys=True))
