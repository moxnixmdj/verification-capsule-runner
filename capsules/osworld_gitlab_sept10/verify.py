from __future__ import annotations
import hashlib, json, urllib.parse, urllib.request
from pathlib import Path

SUBJECT=Path("capsules/osworld_gitlab_sept10/subject.json")
EXPECTED_SUBJECT="d03a0a6d85148017c073b79ee78895cc94870eb3"

def git_blob_sha(path: Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch(url: str):
    req=urllib.request.Request(url,headers={"User-Agent":"Project-Brain-Independent-Verifier","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","replace")

assert git_blob_sha(SUBJECT)==EXPECTED_SUBJECT
s=json.loads(SUBJECT.read_text())
assert s["execution_authority"] is False
assert s["promotion_authority"] is False
assert s["fresh_reality_authority"] is False
assert s["accounting"]["incremental_spend_usd"]==0
assert s["accounting"]["terminal_cases_consumed"]==0
assert s["accounting"]["acceptance_credit_delta"]==0

latest=json.loads(fetch("https://api.github.com/repos/Task-Web/gitlab/commits?until=2026-09-10T23:59:59Z&per_page=10"))
assert latest and latest[0]["sha"]=="8655d651722f4254e59e813de9f68a6732ea525c"
assert latest[0]["commit"]["author"]["date"]=="2026-08-11T11:16:45Z"

between=json.loads(fetch("https://api.github.com/repos/Task-Web/gitlab/commits?since=2026-09-10T00:00:00Z&until=2026-09-20T23:59:59Z&per_page=100"))
assert between==[], between

commit=json.loads(fetch("https://api.github.com/repos/Task-Web/gitlab/commits/8655d651722f4254e59e813de9f68a6732ea525c"))
assert commit["commit"]["tree"]["sha"]=="adeb18dc055b85267c19fbd39a239b47d791d6db"
files={x["filename"]:x["sha"] for x in commit["files"]}
assert files["docker-compose.yml"]=="748ff3d90556ccf17600c08fbaaa65cae9138172"
assert files["README.md"]=="64af03525d5ce423b67827af5407b39272b1f225"

compose=fetch("https://raw.githubusercontent.com/Task-Web/gitlab/8655d651722f4254e59e813de9f68a6732ea525c/docker-compose.yml")
for token in [
    "gitlab/gitlab-ce:18.7.0-ce.0",
    "docker:29.7.2-cli",
    "gitlab/gitlab-runner:alpine-v18.7.0",
]:
    assert token in compose, token

setup=fetch("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/acdd3493808e716825975b0f0208194bb2faf3c3/.codex/skills/setup-osworld/references/gitlab.md")
assert "git clone git@github.com:Task-Web/gitlab.git" in setup
assert "8655d651722f4254e59e813de9f68a6732ea525c" not in setup
assert "git checkout" not in setup

assert s["public_state"]["latest_commit_at_or_before_2026_09_10"]=="8655d651722f4254e59e813de9f68a6732ea525c"
assert s["osworld_setup_reference"]["revision_pin_present"] is False
assert s["verified_if_passes"]["delete"]=="GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY_SEARCH"
assert "NO_ANTHROPIC_REVISION_IDENTITY_CLAIM" in s["hard_nonclaims"]
assert "ANTHROPIC_USED_THIS_EXACT_REVISION_OR_EQUIVALENT_STATE" in s["still_open"]

print("OSWORLD_GITLAB_SEPT10_PUBLIC_STATE_REDUCTION_PASS__ZERO_CREDIT__ANTHROPIC_IDENTITY_OPEN")
