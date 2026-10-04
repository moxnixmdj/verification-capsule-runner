#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

BASE=Path("capsules/root2_current_19_projection/brain")
EXPECTED={
 "ROOT_STATE.json":"e8371418ed39b83b14df874c8eb5e0bdb6a2e603",
 "REACTIVATION.json":"2290a4e553cc0d685fc2a0ecaefe8621fea1c206",
 "MANIFEST.json":"1fba51d15bcfdf6accd90948155517f7c9b98bbb",
 "DAG_ACTIVATION.json":"7ea4dd4edb59c8526bd3993e02f4a8fb53c65085",
 "DAG_VERIFICATION.json":"553602570334f39003708e52d781b8c59f27eb7c",
 "FRONTIER_V18.json":"57d5ee650d4ee250db455d5818899f32aa304918",
 "FRONTIER_V18_VERIFICATION.json":"411089263339c4506b641cf08ba9ac13a50ee4c9",
}
LIVEBENCH="LIVEBENCH_IF_GE_65_7"

def blob_sha(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(name):
    b=(BASE/name).read_bytes()
    got=blob_sha(b)
    assert got==EXPECTED[name],(name,got,EXPECTED[name])
    return json.loads(b)

def main():
    root=load("ROOT_STATE.json")
    react=load("REACTIVATION.json")
    manifest=load("MANIFEST.json")
    activation=load("DAG_ACTIVATION.json")
    dagv=load("DAG_VERIFICATION.json")
    frontier=load("FRONTIER_V18.json")
    frontv=load("FRONTIER_V18_VERIFICATION.json")

    acc=root["current_acceptance"]
    assert (acc["accepted_families"],acc["open_families"],acc["proved_atomic"],acc["unresolved_atomic"])==(5,14,12,26)
    part=root["current_residual_root_partition"]
    assert part["root1_positive_gap_count"]==0
    assert part["root2_only_count"]==16
    assert part["root3_only_count"]==7
    assert part["root2_and_root3_count"]==3
    assert part["unresolved_total"]==26

    root2=set(part["root2_only"])
    mixed=set(part["root2_and_root3"])
    root3=set(part["root3_only"])
    touching=root2|mixed
    assert len(root2)==16 and len(mixed)==3 and len(root3)==7
    assert root2.isdisjoint(mixed) and root2.isdisjoint(root3) and mixed.isdisjoint(root3)
    assert len(touching)==19
    assert LIVEBENCH in root2
    assert LIVEBENCH not in mixed and LIVEBENCH not in root3
    assert part["root1_only_count"]==0 and part["root1_only"]==[]

    manifest_ids={x["id"] for x in manifest["predicates"]}
    assert len(manifest_ids)==19
    assert touching==manifest_ids,(sorted(touching-manifest_ids),sorted(manifest_ids-touching))

    react_ids=set(react["current_root_binding"]["exact_root2_touching_predicates"])
    assert len(react_ids)==19
    assert react_ids==touching
    assert react["current_root_binding"]["root1_positive_gap_count"]==0
    assert react["current_root_binding"]["root2_only_count"]==16
    assert react["current_root_binding"]["root2_and_root3_count"]==3
    assert react["current_root_binding"]["root2_touching_count"]==19
    assert react["current_root_binding"]["git_blob_sha"]==EXPECTED["ROOT_STATE.json"]
    assert react["reused_verified_controller"]["subject_manifest_git_blob_sha"]==EXPECTED["MANIFEST.json"]
    assert react["reused_verified_controller"]["activation_git_blob_sha"]==EXPECTED["DAG_ACTIVATION.json"]
    assert react["reused_verified_controller"]["subject_verification_git_blob_sha"]==EXPECTED["DAG_VERIFICATION.json"]
    assert react["authority"]=={"scheduling":False,"execution":False,"promotion":False,"fresh_reality":False,"acceptance_credit":False}

    assert dagv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert dagv["subject"]["manifest_git_blob_sha"]==EXPECTED["MANIFEST.json"]
    assert dagv["verified"]["predicate_count"]==19
    assert dagv["verified"]["execution_authority"] is False
    assert dagv["verified"]["promotion_authority"] is False
    assert dagv["verified"]["fresh_reality_authority"] is False

    assert activation["subject"]["manifest_git_blob_sha"]==EXPECTED["MANIFEST.json"]
    assert activation["independent_subject_verification"]["git_blob_sha"]==EXPECTED["DAG_VERIFICATION.json"]
    assert activation["projection_verification_required"] is True

    assert frontv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert frontv["subject"]["frontier_git_blob_sha"]==EXPECTED["FRONTIER_V18.json"]
    assert frontv["verified"]["root1_positive_gap_count"]==0
    assert frontv["verified"]["execution_authority"] is False
    assert frontv["verified"]["fresh_reality_authority"] is False

    # Root state explicitly marks the stale frontier authority as false pending this projection.
    ctrl=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
    assert ctrl["effective_scheduling_authority"] is False
    assert root["scheduler_policy"]["root2_current_touching_predicate_count"]==19
    assert root["scheduler_policy"]["root2_effective_scheduling_scope"]=="PENDING_EXACT_CURRENT_19_ROOT2_TOUCHING_RECOMPUTE"

    receipt={
      "schema":"PROJECT_BRAIN_ROOT2_CURRENT_19_PROJECTION_PUBLIC_RUNNER_VERIFICATION_V1",
      "status":"PASS",
      "verified_blobs":EXPECTED,
      "verified":{
        "accepted_families":5,
        "proved_atomic":12,
        "unresolved_atomic":26,
        "root1_positive_gaps":0,
        "root2_only":16,
        "root3_only":7,
        "root2_and_root3":3,
        "root2_touching":19,
        "livebench_root2_only":True,
        "current_root2_set_equals_verified_threshold_dag_manifest_set":True,
        "current_root2_set_equals_reactivation_candidate_set":True,
        "dag_subject_independently_verified":True,
        "frontier_v18_independently_verified":True,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0
      },
      "semantic_effect":"SATISFIES_THE_EXACT_CURRENT_ROOT_PROJECTION_PRECONDITION_FOR_REACTIVATING_THE_ALREADY_VERIFIED_19_PREDICATE_OUTPUT_ONLY_THRESHOLD_DAG_FOR_SCHEDULING_ONLY",
      "hard_nonclaims":[
        "NO_ACCEPTANCE_PREDICATE_CLOSED",
        "NO_EXECUTION_PROMOTION_OR_FRESH_REALITY_AUTHORITY",
        "NO_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT"
      ]
    }
    Path("root2_current_19_projection_verification_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
