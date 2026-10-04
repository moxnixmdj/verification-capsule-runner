#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, sys, urllib.error, urllib.request

EPOCH_DIGEST="5ea710ae6d8b64c9ae990da5bd3ae747806e12843b8c2566bbb1be83d09ab53d"
CLAIM_REF="refs/heads/livebench-v7-claims/"+EPOCH_DIGEST
EXPECTED_DIAGNOSTIC_BLOB="55d4b961f58dc45c1513f9c9282a63773444773d"
EXPECTED_CLASSIFIER_BLOB="44df7313c83914204299953dda81900fae85ab68"
EXPECTED_BASE_EXECUTOR_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

def fail(msg: str) -> "NoReturn":
    raise SystemExit("FAIL_CLOSED:"+msg)

def atomic_claim() -> dict:
    api=os.environ.get("GITHUB_API_URL")
    repo=os.environ.get("GITHUB_REPOSITORY")
    sha=os.environ.get("GITHUB_SHA")
    token=os.environ.get("GH_TOKEN")
    if not all((api,repo,sha,token)):
        fail("GITHUB_ATOMIC_CLAIM_ENV_MISSING")
    if os.environ.get("GITHUB_ACTIONS")!="true":
        fail("NOT_GITHUB_ACTIONS")
    url=f"{api}/repos/{repo}/git/refs"
    payload=json.dumps({"ref":CLAIM_REF,"sha":sha},separators=(",",":")).encode()
    req=urllib.request.Request(url,data=payload,method="POST",headers={
      "Authorization":f"Bearer {token}",
      "Accept":"application/vnd.github+json",
      "Content-Type":"application/json",
      "User-Agent":"project-brain-livebench-v7"
    })
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            status=resp.status
            body=json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code==422:
            fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")
        fail("ATOMIC_ONE_USE_CLAIM_HTTP_"+str(e.code))
    if status!=201:
        fail("ATOMIC_ONE_USE_CLAIM_NOT_201")
    if body.get("ref")!=CLAIM_REF:
        fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_REF_MISMATCH")
    obj=(body.get("object") or {})
    objsha=obj.get("sha")
    if not isinstance(objsha,str) or re.fullmatch(r"[0-9a-f]{40}",objsha) is None:
        fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_SHA_INVALID")
    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_V7_ATOMIC_ONE_USE_CLAIM_RECEIPT_V1",
      "epoch_digest_sha256":EPOCH_DIGEST,
      "claim_ref":CLAIM_REF,
      "create_http_status":201,
      "reference_created":True,
      "response_ref":body.get("ref"),
      "response_object_sha":objsha,
      "uniqueness_linearization_event":"FIRST_ATOMIC_GIT_REF_CREATE_HTTP_201",
      "terminal_dataset_read_before_claim":False,
      "execution_started_before_claim":False,
    }
    print("LIVEBENCH_V7_ATOMIC_CLAIM="+json.dumps(receipt,sort_keys=True),flush=True)
    return receipt

def main() -> int:
    activation_blob=os.environ.get("LIVEBENCH_V7_ACTIVATION_BLOB","")
    if re.fullmatch(r"[0-9a-f]{40}",activation_blob) is None:
        fail("EXACT_ACTIVATION_BLOB_NOT_BOUND")
    # The atomic create is the global one-use linearization point.
    atomic_claim()
    # Import only after claim success. The diagnostic itself reads no terminal
    # dataset until its V6-equivalent zero-case environment setup completes.
    import diagnose_livebench_replay72_v7_sanitized as diagnostic
    return int(diagnostic.main(authorized=True,activation_blob=activation_blob))

if __name__=="__main__":
    raise SystemExit(main())
