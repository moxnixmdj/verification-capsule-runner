from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

SUBJECT=Path("capsules/osworld_v21_official_component_pin/subject.json")
EXPECTED_SUBJECT="be3e5952330fd331768405a9dc2c384812415c7d"

def git_blob_sha(path: Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch_bytes(url: str)->bytes:
    req=urllib.request.Request(url,headers={
        "User-Agent":"Project-Brain-Independent-Verifier",
        "Accept":"application/vnd.github+json"
    })
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def fetch_json(url: str):
    return json.loads(fetch_bytes(url).decode("utf-8","replace"))

assert git_blob_sha(SUBJECT)==EXPECTED_SUBJECT
s=json.loads(SUBJECT.read_text())
assert s["execution_authority"] is False
assert s["promotion_authority"] is False
assert s["fresh_reality_authority"] is False
assert s["accounting"]["incremental_spend_usd"]==0
assert s["accounting"]["terminal_cases_consumed"]==0
assert s["accounting"]["acceptance_credit_delta"]==0

tag=fetch_json("https://api.github.com/repos/xlang-ai/OSWorld-V2/git/ref/tags/osworld-v2.1")
assert tag["object"]["type"]=="commit"
assert tag["object"]["sha"]=="3d778a3c9a34a079316f70df023b166700445792"

manifest_bytes=fetch_bytes("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/benchmark_releases/osworld-v2.1.json")
manifest=json.loads(manifest_bytes.decode("utf-8"))
assert manifest["release"]=="osworld-v2.1"
assert manifest["status"]=="active"
assert manifest["osworld_code"]["base_commit"]=="325ab352e2ff7410854bf8e3324c391bc60e7526"
assert manifest["tasks"]["commit"]=="0a1aadad95aa79b00b3783e717d865089ab06e26"
assert manifest["assets"]["commit"]=="384b3834faba5700a7b589e6cc181490c9808949"
assert manifest["public_assets"]["commit"]=="3a140a3df8f351b22bb5b9526846f078e738777f"
assert manifest["website_code"]["commit"]=="60c89fe6a8ed934668619d8d26132848239eb8ee"
assert manifest["task_hash_manifest"]["task_count"]==108
assert manifest["task_hash_manifest"]["sha256"]=="sha256:c54d428329be5ca72742a6becd49ee83cf739df5dea429bba182e1f3f21badfb"

hash_bytes=fetch_bytes("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/benchmark_releases/osworld-v2.1.task_hashes.json")
assert "sha256:"+hashlib.sha256(hash_bytes).hexdigest()==manifest["task_hash_manifest"]["sha256"]

docker=manifest["provider_images"]["docker"]["ubuntu"]
assert docker["artifact_size"]==14891811084
assert docker["artifact_sha256"]=="sha256:14b08aa7ba6c023ecb91d46de8df5de32af4d1d6bd75ea925519caf9677fc8b3"
assert docker["runtime_image"]=="happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9"
assert docker["artifact_revision"]=="6e16459a2feb5a8f1ed65babcfe7a2a6205d049d"
assert manifest["provider_images"]["aws"]["ubuntu"]["us-east-1"]["1920x1080"]["ami_id"]=="ami-01017272139e01feb"

webtag=fetch_json("https://api.github.com/repos/Task-Web/OSWorld-web/git/ref/tags/osworld-v2.1")
assert webtag["object"]["type"]=="commit"
assert webtag["object"]["sha"]=="60c89fe6a8ed934668619d8d26132848239eb8ee"

assert manifest["verification"]["blockers"]==[]
limits=set(manifest["verification"]["limitations"])
assert "No full 108-task agent evaluation." in limits
assert any("AWS/Docker guest equivalence is not established" in x for x in limits)
assert any("No hosted website deployment verification" in x for x in limits)
assert any("Task029" in x and "no clean Task029 setup pass is claimed" in x for x in limits)

o=s["official_release"]
assert o["tasks"]["task_count"]==108
assert o["tasks"]["commit"]==manifest["tasks"]["commit"]
assert o["gated_assets"]["commit"]==manifest["assets"]["commit"]
assert o["public_assets"]["commit"]==manifest["public_assets"]["commit"]
assert o["website"]["commit"]==manifest["website_code"]["commit"]
assert o["provider_images"]["docker_artifact_sha256"]==docker["artifact_sha256"]
assert o["provider_images"]["docker_runtime_image"]==docker["runtime_image"]

deletes=set(s["verified_if_passes"]["delete"])
assert deletes=={
    "GENERIC_OSWORLD_V21_RELEASE_IDENTITY_SEARCH",
    "GENERIC_OSWORLD_V21_TASK_COUNT_AND_TASK_REVISION_SEARCH",
    "GENERIC_OSWORLD_V21_GATED_ASSET_REVISION_SEARCH",
    "GENERIC_OSWORLD_V21_WEBSITE_REVISION_SEARCH",
    "GENERIC_OSWORLD_V21_PROVIDER_IMAGE_IDENTITY_SEARCH",
}
preserve=set(s["verified_if_passes"]["preserve"])
for needed in [
    "HUGGING_FACE_OSWORLD_GATED_ASSET_ACCOUNT_ACCESS",
    "ANTHROPIC_EXACT_GITLAB_IDENTITY_OR_PROTOCOL_EQUIVALENCE",
    "SELF_HOST_RUNTIME_AND_TOKEN_REACHABILITY",
    "END_TO_END_PROTOCOL_EQUIVALENCE",
    "OPUS_4_8_GRADER_ROUTE",
    "BRAIN_SCORE",
]:
    assert needed in preserve

assert "NO_CLAIM_ANTHROPIC_USED_EVERY_OFFICIAL_V21_COMPONENT_BYTE_IDENTITY" in s["hard_nonclaims"]
assert "NO_BRAIN_SCORE" in s["hard_nonclaims"]
assert "NO_FRESH_REALITY" in s["hard_nonclaims"]

print("OSWORLD_V21_OFFICIAL_COMPONENT_PIN_REDUCTION_PASS__FIVE_GENERIC_IDENTITY_SEARCH_CLASSES_DELETABLE__COMPARATOR_RUNTIME_SCORE_OPEN__ZERO_CREDIT")
