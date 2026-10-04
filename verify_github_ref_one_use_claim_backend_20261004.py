from __future__ import annotations
import json, os, urllib.error, urllib.parse, urllib.request

repo=os.environ["GITHUB_REPOSITORY"]
owner,name=repo.split("/",1)
token=os.environ["GITHUB_TOKEN"]
sha=os.environ["GITHUB_SHA"].lower()
run_id=os.environ["GITHUB_RUN_ID"]
attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
ref=f"refs/heads/shadow-claim-verification/v1/{run_id}-{attempt}"
url=f"https://api.github.com/repos/{owner}/{name}/git/refs"
headers={
    "Accept":"application/vnd.github+json",
    "Authorization":f"Bearer {token}",
    "X-GitHub-Api-Version":"2026-03-10",
    "Content-Type":"application/json",
    "User-Agent":"project-brain-claim-backend-verifier-v1",
}
body=json.dumps({"ref":ref,"sha":sha},separators=(",",":")).encode()

def post():
    req=urllib.request.Request(url,data=body,method="POST",headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            return int(r.status),json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try: payload=json.loads(raw)
        except Exception: payload={"raw":raw}
        return int(e.code),payload

first_status,first=post()
assert first_status==201,(first_status,first)
assert first.get("ref")==ref,first
assert str((first.get("object") or {}).get("sha") or "").lower()==sha,first

# Read the durable reference back before attempting replay.
encoded=urllib.parse.quote(ref.removeprefix("refs/"),safe="/")
get_req=urllib.request.Request(
    f"https://api.github.com/repos/{owner}/{name}/git/ref/{encoded}",
    headers={k:v for k,v in headers.items() if k!="Content-Type"},
)
with urllib.request.urlopen(get_req,timeout=30) as r:
    observed=json.loads(r.read().decode())
assert observed.get("ref")==ref,observed
assert str((observed.get("object") or {}).get("sha") or "").lower()==sha,observed

second_status,second=post()
assert second_status in {409,422},(second_status,second)
errors=second.get("errors") if isinstance(second,dict) else None

print(json.dumps({
    "status":"PASS",
    "backend":"GITHUB_CREATE_GIT_REFERENCE",
    "repository":repo,
    "claim_ref":ref,
    "target_sha":sha,
    "first_create_http_status":first_status,
    "durable_readback_matches":True,
    "replay_http_status":second_status,
    "replay_rejected":True,
    "github_error_codes":[
        str(x.get("code")) for x in (errors or []) if isinstance(x,dict) and x.get("code")
    ],
    "claim_key_unique_by_ref":True,
    "zero_incremental_spend":True,
},sort_keys=True))
