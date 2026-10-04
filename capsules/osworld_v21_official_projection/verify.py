from __future__ import annotations
import hashlib, json
from pathlib import Path

BASE=Path("capsules/osworld_v21_official_projection")
EXPECTED={
    "subject.json":"be3e5952330fd331768405a9dc2c384812415c7d",
    "receipt.json":"ddd50cd5fcf7762ebd8ad6b66fff3a6bfc149650",
    "activation.json":"f6d7cdc2924aaf91ea69fe5afccf584131a66355",
    "root_state.json":"90dbeaf74cda18edd38d1cc34a003b4fffd236a0",
    "terminal_authority.json":"9ed6b29ee0fc0f7edb6545dd1312731009e902f7",
}

def git_blob_sha(path: Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for name,sha in EXPECTED.items():
    assert git_blob_sha(BASE/name)==sha,(name,git_blob_sha(BASE/name),sha)

subject=json.loads((BASE/"subject.json").read_text())
receipt=json.loads((BASE/"receipt.json").read_text())
activation=json.loads((BASE/"activation.json").read_text())
root=json.loads((BASE/"root_state.json").read_text())
auth=json.loads((BASE/"terminal_authority.json").read_text())

assert receipt["subject"]["git_blob_sha"]==EXPECTED["subject.json"]
assert receipt["independent_runner"]["pull_request"]==1672
assert receipt["independent_runner"]["workflow_run_id"]==37175225327
assert receipt["independent_runner"]["workflow_job_id"]==111356352631
assert receipt["independent_runner"]["conclusion"]=="success"

assert activation["subject"]["git_blob_sha"]==EXPECTED["subject.json"]
assert activation["verification"]["git_blob_sha"]==EXPECTED["receipt.json"]
assert activation["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert activation["authority"]=={
    "scheduling":True,
    "execution":False,
    "promotion":False,
    "fresh_reality":False,
}

deleted=set(activation["effects"]["delete"])
expected_deleted={
    "GENERIC_OSWORLD_V21_RELEASE_IDENTITY_SEARCH",
    "GENERIC_OSWORLD_V21_TASK_COUNT_AND_TASK_REVISION_SEARCH",
    "GENERIC_OSWORLD_V21_GATED_ASSET_REVISION_SEARCH",
    "GENERIC_OSWORLD_V21_WEBSITE_REVISION_SEARCH",
    "GENERIC_OSWORLD_V21_PROVIDER_IMAGE_IDENTITY_SEARCH",
}
assert deleted==expected_deleted

p=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["primary_source_search_deletions"]
assert p["scheduler_deletion_count"]==6
assert p["effective_scheduler_deletion_count"]==11
supp=p["supplemental_activations"]
assert len(supp)==1
assert supp[0]["activation_git_blob_sha"]==EXPECTED["activation.json"]
assert supp[0]["verification_git_blob_sha"]==EXPECTED["receipt.json"]
assert set(supp[0]["deleted"])==expected_deleted

sp=root["scheduler_policy"]
assert sp["root2_osworld_v21_official_component_pin_reduction"]=="canonical/governance/OSWORLD_V21_OFFICIAL_COMPONENT_PIN_REDUCTION_ACTIVATION_V1.json"
assert sp["repeat_search_for_verified_osworld_v21_official_component_identity_forbidden"] is True
assert sp["fresh_reality_before_zero_reality_fixed_point"] is False

acc=root["current_acceptance"]
assert acc["accepted_families"]==5
assert acc["open_families"]==14
assert acc["proved_atomic"]==12
assert acc["unresolved_atomic"]==26
assert acc["terminal"] is False

a=auth["authorities"]["osworld_v21_official_component_pin_reduction"]
assert a["activation_git_blob_sha"]==EXPECTED["activation.json"]
assert a["subject_git_blob_sha"]==EXPECTED["subject.json"]
assert a["verification_git_blob_sha"]==EXPECTED["receipt.json"]
assert a["execution_authority"] is False
assert a["promotion_authority"] is False
assert a["fresh_reality_authority"] is False
assert a["target_predicate"]=="OSWORLD_2_1_PARTIAL_GE_81_8"

for residual in activation["effects"]["preserve"]:
    assert residual in a["preserved_residual"]

assert subject["accounting"]["incremental_spend_usd"]==0
assert activation["accounting"]["incremental_spend_usd"]==0
assert activation["accounting"]["terminal_cases_consumed"]==0

print("OSWORLD_V21_OFFICIAL_COMPONENT_PIN_FINAL_PROJECTION_PASS__11_TOTAL_PRIMARY_SOURCE_SEARCH_DELETIONS__5_NEW_OSWORLD_IDENTITY_DELETIONS__RUNTIME_COMPARATOR_SCORE_OPEN__ZERO_CREDIT")
