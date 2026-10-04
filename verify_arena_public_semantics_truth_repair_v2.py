from __future__ import annotations
import hashlib, json
from pathlib import Path

BASE=Path("capsules/arena-public-semantics-truth-repair-v1")
FILES={
 "ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json":"d7a7165630bd2963c78d5e7f4fbd2f286e57334a",
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":"3fafe7ec793ed1b2419b268d6559be3f01fbfacf",
 "CURRENT_TERMINAL_AUTHORITY_V1.json":"ce7dd92470b8767e7ef0390457ddab77df928a58",
}
def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(name:str)->dict:
    p=BASE/name
    data=p.read_bytes()
    assert blob_sha(data)==FILES[name], (name, blob_sha(data), FILES[name])
    return json.loads(data)

def main()->dict:
    repair=load("ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json")
    root=load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
    current=load("CURRENT_TERMINAL_AUTHORITY_V1.json")

    assert repair["observed_now"]["authenticated_api_portal_existence_publicly_reproducible"] is True
    assert repair["observed_now"]["endpoint_and_routing_semantics_unauthenticated_publicly_reproducible"] is False
    gated=set(repair["corrected_classification"]["login_gated_or_account_specific"])
    for x in {
      "GET_V1_MODELS_ENDPOINT_SEMANTICS",
      "DIRECT_MODEL_PARAMETER_ROUTING_SEMANTICS",
      "FALLBACK_CONTROL_SEMANTICS",
      "RESOLVED_MODEL_RESPONSE_HEADER_SEMANTICS",
      "ACCOUNT_MODEL_LIST_INCLUDES_EXACT_REQUIRED_OPUS55_VARIANT",
      "ZERO_INCREMENTAL_SPEND_ENTITLEMENT_OR_PREEXISTING_CREDIT",
      "FROZEN_HARNESS_AND_EFFORT_COMPARABILITY",
    }:
        assert x in gated

    for ptr in (
      root["scheduler_policy"]["arena_public_semantics_truth_repair"],
      current["arena_public_semantics_truth_repair"],
    ):
        assert ptr["path"]=="canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json"
        assert ptr["git_blob_sha"]=="d7a7165630bd2963c78d5e7f4fbd2f286e57334a"
        assert ptr["scheduling_authority"] is True
        assert ptr["execution_authority"] is False
        assert ptr["promotion_authority"] is False
        assert ptr["fresh_reality_authority"] is False

    ca=root["current_acceptance"]
    assert (ca["accepted_families"],ca["proved_atomic"],ca["unresolved_atomic"],ca["terminal"])==(5,12,26,False)
    assert repair["execution_authority"] is False
    assert repair["promotion_authority"] is False
    assert repair["fresh_reality_authority"] is False
    assert repair["accounting"]["acceptance_credit_delta"]==0
    return {
      "schema":"PROJECT_BRAIN_ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_INDEPENDENT_CAPSULE_V2",
      "status":"PASS",
      "exact_blob_identity":True,
      "unauthenticated_public_overclaim_repaired":True,
      "terminal_counts_preserved":True,
      "acceptance_credit_delta":0,
      "fresh_reality_authority":False
    }

if __name__=="__main__":
    print(json.dumps(main(),sort_keys=True))
