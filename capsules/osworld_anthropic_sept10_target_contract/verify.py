from __future__ import annotations
import hashlib, html, json, re, urllib.request
from pathlib import Path

SUBJECT=Path("capsules/osworld_anthropic_sept10_target_contract/subject.json")
EXPECTED_SUBJECT="be1c2cd45cd8b7697649ad50d70ed6fce71fc691"

def git_blob_sha(path: Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch(url: str, accept: str="text/html,*/*")->str:
    req=urllib.request.Request(url, headers={
        "User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier",
        "Accept":accept,
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8","replace")

def normalized_text(raw: str)->str:
    raw=html.unescape(raw)
    raw=re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I|re.S)
    raw=re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.I|re.S)
    raw=re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()

assert git_blob_sha(SUBJECT)==EXPECTED_SUBJECT
s=json.loads(SUBJECT.read_text())
assert s["execution_authority"] is False
assert s["promotion_authority"] is False
assert s["fresh_reality_authority"] is False
assert s["accounting"]["incremental_spend_usd"]==0
assert s["accounting"]["terminal_cases_consumed"]==0
assert s["accounting"]["acceptance_credit_delta"]==0
assert s["target_predicate"]=="OSWORLD_2_1_PARTIAL_GE_81_8"

# Primary target-side methodology disclosure.
raw=fetch("https://www.anthropic.com/claude-opus-5-5-system-card")
t=normalized_text(raw)
checks=[
    "OSWorld 2.0",
    "108 long-horizon computer use tasks",
    "1080p resolution",
    "maximum of 500 action steps per task",
    "Claude Opus 4.8",
    "September 10, 2026",
    "task files, task assets, and companion web applications",
    "retains every screenshot",
    "100k tokens",
    "partial score of 81.8%",
    "strict pass rate of 48.7%",
    "five independent runs",
]
missing=[x for x in checks if x not in t]
assert not missing, ("ANTHROPIC_PRIMARY_TEXT_MISSING", missing)

# Recompute the unique public Task-Web/gitlab state for the disclosed Sep-10 snapshot date.
latest=json.loads(fetch("https://api.github.com/repos/Task-Web/gitlab/commits?until=2026-09-10T23:59:59Z&per_page=10","application/vnd.github+json"))
assert latest and latest[0]["sha"]=="8655d651722f4254e59e813de9f68a6732ea525c"
between=json.loads(fetch("https://api.github.com/repos/Task-Web/gitlab/commits?since=2026-09-10T00:00:00Z&until=2026-09-20T23:59:59Z&per_page=100","application/vnd.github+json"))
assert between==[], between

# Verify OSWorld's public setup reference includes Task-Web/gitlab as a companion service and does not pin a different revision.
setup=fetch("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/acdd3493808e716825975b0f0208194bb2faf3c3/.codex/skills/setup-osworld/references/gitlab.md","text/plain")
assert "Task-Web/gitlab.git" in setup
assert "8655d651722f4254e59e813de9f68a6732ea525c" not in setup
assert "git checkout" not in setup

c=s["primary_target_evidence"]["directly_disclosed_contract"]
assert c["task_count"]==108
assert c["display_resolution"]=="1080P"
assert c["maximum_action_steps_per_task"]==500
assert c["benchmark_snapshot_date"]=="2026-09-10"
assert c["opus55_partial_score_pct"]==81.8
assert c["opus55_strict_pass_pct"]==48.7

prem=s["composition_theorem"]["premises"]
assert any("2026_09_10_VERSION" in x for x in prem)
assert "8655D651722F4254E59E813DE9F68A6732EA525C" in s["composition_theorem"]["conclusion"]
deletes=s["scheduler_effect_if_independently_verified"]["delete"]
assert "ANTHROPIC_USED_THIS_EXACT_GITLAB_REVISION_OR_EQUIVALENT_STATE_AS_AN_OPEN_FACT" in deletes
assert "NO_OSWORLD_PREDICATE_CLOSURE" in s["hard_nonclaims"]
assert "NO_CLAIM_THE_2026_09_16_OFFICIAL_OSWORLD_V2_1_RELEASE_EQUALS_THE_ANTHROPIC_2026_09_10_SNAPSHOT" in s["hard_nonclaims"]

print("OSWORLD_ANTHROPIC_SEPT10_TARGET_PROTOCOL_BINDING_PASS__GITLAB_IDENTITY_REDUCED__ZERO_CREDIT")
