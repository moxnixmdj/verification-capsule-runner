#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_CANDIDATE_BLOB="f58c12d5c42e1e6b7cdda05d52f978469f3aa300"

def blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def get(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-zero-reality-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

candidate_raw=(ROOT/"candidate.json").read_bytes()
assert blob_sha(candidate_raw)==EXPECTED_CANDIDATE_BLOB,(blob_sha(candidate_raw),EXPECTED_CANDIDATE_BLOB)
candidate=json.loads(candidate_raw)

manifest_raw=get("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/benchmark_releases/osworld-v2.1.json")
readme_raw=get("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/README.md")
assert blob_sha(manifest_raw)=="6d37c6f4c6c4f6daa5077d4e4c828f68360b7e36"
assert blob_sha(readme_raw)=="1dc05f1acee1412c92e7f103a518fc128f7d14cb"
manifest=json.loads(manifest_raw)
readme=readme_raw.decode("utf-8")

assert manifest["release"]=="osworld-v2.1"
assert manifest["website_code"]["repository"]=="Task-Web/OSWorld-web"
assert manifest["website_code"]["tag"]=="osworld-v2.1"
assert manifest["website_code"]["commit"]=="60c89fe6a8ed934668619d8d26132848239eb8ee"
assert manifest["tasks"]["commit"]=="0a1aadad95aa79b00b3783e717d865089ab06e26"
assert manifest["assets"]["commit"]=="384b3834faba5700a7b589e6cc181490c9808949"
assert "gitlab" not in json.dumps(manifest).lower()

tree=json.loads(get("https://api.github.com/repos/Task-Web/OSWorld-web/git/trees/60c89fe6a8ed934668619d8d26132848239eb8ee").decode("utf-8"))
gitlinks=[x for x in tree.get("tree",[]) if x.get("mode")=="160000" and x.get("type")=="commit"]
assert tree["sha"]=="60c89fe6a8ed934668619d8d26132848239eb8ee"
assert len(gitlinks)==25,len(gitlinks)
paths={x["path"] for x in gitlinks}
assert {"mailhub_web","cloudcrm_web","overleaf_web","teamchat_web","awsconsole_web"}.issubset(paths)

assert "Task-Web/OSWorld-web@osworld-v2.1" in readme
assert "xlangai/osworld_v2_tasks" in readme
assert "xlangai/osworld_v2_assets_gated" in readme
assert "your request will automatically be approved" in readme
assert "Task-Web/gitlab" in readme
assert 'export GITLAB_URL="<your-gitlab-url>"' in readme
assert 'export GITLAB_PRIVATE_TOKEN="<your-private-token>"' in readme

assert candidate["website_source"]["source_identity"]=="EXACTLY_PINNED"
assert candidate["website_source"]["gitlink_count"]==25
assert candidate["gitlab"]["upstream_release_pinned_revision_found"] is False
assert candidate["gated_population_and_assets"]["material_account_access"]=="UNPROVED"
assert candidate["terminal_cases_consumed"]==0
assert candidate["acceptance_credit_delta"]==0
assert candidate["fresh_reality_authority"] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_RELEASE_SOURCE_GRAPH__WEBSITE_PINNED__GITLAB_REVISION_UNPINNED__GATED_ACCESS_ACCOUNT_BOUND__ZERO_CASE__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "candidate_exact_blob":True,
    "release_manifest_exact_blob":True,
    "release_readme_exact_blob":True,
    "website_commit_exact":True,
    "website_gitlinks_25":True,
    "tasks_assets_revisions_exact":True,
    "gated_access_autoapproval_wording":True,
    "gitlab_repository_named":True,
    "gitlab_release_revision_absent":True
  },
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False,
  "fresh_reality_authority":False
},indent=2,sort_keys=True))
