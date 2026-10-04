#!/usr/bin/env python3
from __future__ import annotations
import json,os,re,urllib.error,urllib.request
EPOCH_DIGEST="a2c7b719fa717f476426d92cc0bc1828ebfc13800734a4ec84043287c79132cd"
CLAIM_REF="refs/heads/livebench-v9-retry2-claims/"+EPOCH_DIGEST
EXPECTED_ACTIVATION_BLOB="424531d02dfc2e8098a81d57fb46140fc999db12"
def fail(msg): raise SystemExit("FAIL_CLOSED:"+msg)
def atomic_claim():
    api=os.environ.get("GITHUB_API_URL");repo=os.environ.get("GITHUB_REPOSITORY")
    sha=os.environ.get("GITHUB_SHA");token=os.environ.get("GH_TOKEN")
    if not all((api,repo,sha,token)) or os.environ.get("GITHUB_ACTIONS")!="true": fail("GITHUB_ATOMIC_CLAIM_ENV_MISSING")
    req=urllib.request.Request(f"{api}/repos/{repo}/git/refs",
      data=json.dumps({"ref":CLAIM_REF,"sha":sha},separators=(",",":")).encode(),method="POST",
      headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"project-brain-livebench-v9-retry2"})
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            status=resp.status;body=json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")
        fail("ATOMIC_ONE_USE_CLAIM_HTTP_"+str(exc.code))
    objsha=(body.get("object") or {}).get("sha")
    if status!=201 or body.get("ref")!=CLAIM_REF or not isinstance(objsha,str) or re.fullmatch(r"[0-9a-f]{40}",objsha) is None:
        fail("ATOMIC_ONE_USE_CLAIM_INVALID")
    print("LIVEBENCH_V9_RETRY2_ATOMIC_CLAIM="+json.dumps({
      "epoch_digest_sha256":EPOCH_DIGEST,"claim_ref":CLAIM_REF,"create_http_status":201,
      "reference_created":True,"response_object_sha":objsha,
      "terminal_dataset_read_before_claim":False,"execution_started_before_claim":False},sort_keys=True),flush=True)
def main():
    if os.environ.get("LIVEBENCH_V9_RETRY2_ACTIVATION_BLOB")!=EXPECTED_ACTIVATION_BLOB: fail("EXACT_ACTIVATION_BLOB_MISMATCH")
    atomic_claim()
    import diagnose_livebench_replay72_v9_preacquisition as diagnostic
    return int(diagnostic.main(authorized=True,activation_blob=EXPECTED_ACTIVATION_BLOB))
if __name__=="__main__": raise SystemExit(main())
