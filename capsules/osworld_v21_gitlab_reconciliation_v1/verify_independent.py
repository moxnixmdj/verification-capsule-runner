from __future__ import annotations
import hashlib, json, pathlib, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED=json.loads((ROOT/"EXPECTED.json").read_text(encoding="utf-8"))

def git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def fetch_raw(path:str)->bytes:
    url=f"https://raw.githubusercontent.com/{EXPECTED['upstream_repo']}/{EXPECTED['upstream_ref']}/{path}"
    with urllib.request.urlopen(url,timeout=60) as r:
        return r.read()

candidate_path=ROOT/"brain/OSWORLD_V21_GITLAB_PROTOCOL_RECONCILIATION_V1.json"
candidate_raw=candidate_path.read_bytes()
assert git_blob_sha(candidate_raw)==EXPECTED["brain_candidate_blob"]
candidate=json.loads(candidate_raw)

docs={}
for path,sha in EXPECTED["upstream_blobs"].items():
    raw=fetch_raw(path)
    got=git_blob_sha(raw)
    assert got==sha,(path,got,sha)
    docs[path]=raw.decode("utf-8")

manifest=json.loads(docs["benchmark_releases/osworld-v2.1.json"])
contract=docs["benchmark_releases/README.md"]
skill=docs[".codex/skills/setup-osworld/SKILL.md"]
gitlab=docs[".codex/skills/setup-osworld/references/gitlab.md"]
guide=docs["docs/PUBLIC_EVALUATION_GUIDELINE_v2.1.md"]

# The official release manifest pins code/tasks/assets/website/provider images.
for key in ("osworld_code","website_code","tasks","assets","provider_images"):
    assert key in manifest
assert "gitlab" not in manifest
assert "gitlab_code" not in manifest
assert "gitlab_revision" not in manifest

# The release manifest contract explicitly enumerates comparable release inputs.
for literal in ("osworld_code","website_code","tasks","assets","provider_images"):
    assert literal in contract
assert "GitLab" not in contract and "gitlab" not in contract

# Versioned setup treats GitLab as an optional/shared service procedure, not a release-pinned component.
assert "GitLab server, using `Task-Web/gitlab`" in skill
assert "These service procedures are shared" in skill
assert "Read the selected release manifest for exact component references" in skill
assert "GitLab and proxy" in skill

# GitLab service success is reachability + token/API behavior.
assert "The goal is a\nreachable GitLab URL and valid private token" in gitlab
assert 'curl -fsS --max-time 30 "$GITLAB_URL/users/sign_in"' in gitlab
assert '"$GITLAB_URL/api/v4/user"' in gitlab

# Public evaluation protocol requires URL + token for GitLab-backed tasks.
assert 'export GITLAB_URL="<your-gitlab-url>"' in guide
assert 'export GITLAB_PRIVATE_TOKEN="<your-private-token>"' in guide
assert "Required only for GitLab-backed tasks." in guide

# Candidate must delete only the unsupported exact-revision requirement and preserve functional gates.
logic=candidate["logical_reconciliation"]
assert logic["deleted_brain_requirement"]=="GITLAB_EXACT_REVISION_OR_INDEPENDENT_EQUIVALENCE_BINDING"
req=set(logic["replacement_load_bearing_requirements"])
for x in ("SELF_HOST_TASK_WEB_GITLAB_USING_THE_SHARED_UPSTREAM_PROCEDURE",
          "GITLAB_URL_REACHABLE",
          "GITLAB_PRIVATE_TOKEN_VALID",
          "REQUIRED_GITLAB_API_BEHAVIOR_FOR_SELECTED_TASKS_VERIFIED_BY_PROTOCOL_PREFLIGHT"):
    assert x in req
assert logic["current_task_web_gitlab_main_head_is_not_promoted_to_FROZEN_REFERENCE"] is True

# Zero-credit / no-execution invariants.
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert candidate[k]==0
assert candidate["execution_authority"] is False
assert candidate["promotion_authority"] is False
assert candidate["fresh_reality_authority"] is False
assert candidate["terminal_cases_consumed"]==0
assert candidate["incremental_spend_usd"]==0

print("OSWORLD_V21_GITLAB_RECONCILIATION_INDEPENDENT_PASS")
