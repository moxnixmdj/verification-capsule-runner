#!/usr/bin/env python3
from __future__ import annotations
import json,os,re,urllib.error,urllib.request

EPOCH_DIGEST="e2f1f2a8d42165e7ba4ecf07a87df0a347ca70143211c4e39e18d4689129c543"
CLAIM_REF="refs/heads/livebench-v9-claims/"+EPOCH_DIGEST
EXPECTED_ACTIVATION_BLOB="93457b91a91c96befcc0c5f2dcf2eaa55a0529e3"

def fail(msg):
    raise SystemExit("FAIL_CLOSED:"+msg)

def atomic_claim():
    api=os.environ.get("GITHUB_API_URL");repo=os.environ.get("GITHUB_REPOSITORY")
    sha=os.environ.get("GITHUB_SHA");token=os.environ.get("GH_TOKEN")
    if not all((api,repo,sha,token)) or os.environ.get("GITHUB_ACTIONS")!="true":
        fail("GITHUB_ATOMIC_CLAIM_ENV_MISSING")
    req=urllib.request.Request(
        f"{api}/repos/{repo}/git/refs",
        data=json.dumps({"ref":CLAIM_REF,"sha":sha},separators=(",",":")).encode(),
        method="POST",
        headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"project-brain-livebench-v9"},
    )
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            status=resp.status;body=json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")
        fail("ATOMIC_ONE_USE_CLAIM_HTTP_"+str(exc.code))
    if status!=201: fail("ATOMIC_ONE_USE_CLAIM_NOT_201")
    if body.get("ref")!=CLAIM_REF: fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_REF_MISMATCH")
    objsha=(body.get("object") or {}).get("sha")
    if not isinstance(objsha,str) or re.fullmatch(r"[0-9a-f]{40}",objsha) is None:
        fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_SHA_INVALID")
    print("LIVEBENCH_V9_ATOMIC_CLAIM="+json.dumps({
      "epoch_digest_sha256":EPOCH_DIGEST,
      "claim_ref":CLAIM_REF,
      "create_http_status":201,
      "reference_created":True,
      "response_object_sha":objsha,
      "terminal_dataset_read_before_claim":False,
      "execution_started_before_claim":False,
    },sort_keys=True),flush=True)

def main():
    activation_blob=os.environ.get("LIVEBENCH_V9_ACTIVATION_BLOB","")
    if activation_blob!=EXPECTED_ACTIVATION_BLOB:
        fail("EXACT_ACTIVATION_BLOB_MISMATCH")
    atomic_claim()
    import diagnose_livebench_replay72_v9_preacquisition as diagnostic
    return int(diagnostic.main(authorized=True,activation_blob=activation_blob))

if __name__=="__main__":
    raise SystemExit(main())
