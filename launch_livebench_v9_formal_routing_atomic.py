#!/usr/bin/env python3
from __future__ import annotations
import json,os,re,urllib.error,urllib.request

EPOCH_DIGEST="5bc110694f940f04014542c9660b98983fc178ae8489fee6db4e1e3b822c9c05"
CLAIM_REF="refs/heads/livebench-v9-claims/"+EPOCH_DIGEST

def fail(msg):
    raise SystemExit("FAIL_CLOSED:"+msg)

def atomic_claim():
    api=os.environ.get("GITHUB_API_URL"); repo=os.environ.get("GITHUB_REPOSITORY")
    sha=os.environ.get("GITHUB_SHA"); token=os.environ.get("GH_TOKEN")
    if not all((api,repo,sha,token)) or os.environ.get("GITHUB_ACTIONS")!="true":
        fail("GITHUB_ATOMIC_CLAIM_ENV_MISSING")
    url=f"{api}/repos/{repo}/git/refs"
    payload=json.dumps({"ref":CLAIM_REF,"sha":sha},separators=(",",":")).encode()
    req=urllib.request.Request(url,data=payload,method="POST",headers={
      "Authorization":f"Bearer {token}","Accept":"application/vnd.github+json",
      "Content-Type":"application/json","User-Agent":"project-brain-livebench-v9"
    })
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            status=resp.status; body=json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")
        fail("ATOMIC_ONE_USE_CLAIM_HTTP_"+str(e.code))
    if status!=201: fail("ATOMIC_ONE_USE_CLAIM_NOT_201")
    if body.get("ref")!=CLAIM_REF: fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_REF_MISMATCH")
    objsha=(body.get("object") or {}).get("sha")
    if not isinstance(objsha,str) or re.fullmatch(r"[0-9a-f]{40}",objsha) is None:
        fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_SHA_INVALID")
    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_V9_ATOMIC_ONE_USE_CLAIM_RECEIPT_V1",
      "epoch_digest_sha256":EPOCH_DIGEST,"claim_ref":CLAIM_REF,
      "create_http_status":201,"reference_created":True,
      "response_ref":body.get("ref"),"response_object_sha":objsha,
      "terminal_dataset_read_before_claim":False,"execution_started_before_claim":False,
      "uniqueness_linearization_event":"FIRST_ATOMIC_GIT_REF_CREATE_HTTP_201"
    }
    print("LIVEBENCH_V9_ATOMIC_CLAIM="+json.dumps(out,sort_keys=True),flush=True)

def main():
    activation_blob=os.environ.get("LIVEBENCH_V9_ACTIVATION_BLOB","")
    if re.fullmatch(r"[0-9a-f]{40}",activation_blob or "") is None:
        fail("EXACT_ACTIVATION_BLOB_NOT_BOUND")
    atomic_claim()
    import diagnose_livebench_replay72_v9_formal_routing as diagnostic
    return int(diagnostic.main(authorized=True,activation_blob=activation_blob))

if __name__=="__main__":
    raise SystemExit(main())
