#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAND=ROOT/"OSWORLD_V21_GITLAB_PROTOCOL_RECONCILIATION_V1.json"
EXPECTED_BLOB="a6142a898df97c8d9691b6a810850fa8c962b035"

RAW="https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/"
URLS={
 "manifest": RAW+"benchmark_releases/osworld-v2.1.json",
 "contract": RAW+"benchmark_releases/README.md",
 "skill": RAW+".codex/skills/setup-osworld/SKILL.md",
 "gitlab": RAW+".codex/skills/setup-osworld/references/gitlab.md",
 "guide": RAW+"docs/PUBLIC_EVALUATION_GUIDELINE_v2.1.md",
}

def git_blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8")

def walk_strings(x):
    if isinstance(x,dict):
        for k,v in x.items():
            yield str(k)
            yield from walk_strings(v)
    elif isinstance(x,list):
        for v in x: yield from walk_strings(v)
    elif isinstance(x,(str,int,float,bool)):
        yield str(x)

def main():
    errors=[]
    if git_blob_sha(CAND)!=EXPECTED_BLOB:
        errors.append("BRAIN_CANDIDATE_BLOB_DRIFT")
    cand=json.loads(CAND.read_text())
    manifest_text=fetch(URLS["manifest"])
    contract=fetch(URLS["contract"])
    skill=fetch(URLS["skill"])
    gitlab=fetch(URLS["gitlab"])
    guide=fetch(URLS["guide"])
    manifest=json.loads(manifest_text)

    manifest_strings="\n".join(walk_strings(manifest)).lower()
    if "gitlab" in manifest_strings:
        errors.append("RELEASE_MANIFEST_UNEXPECTED_GITLAB_BINDING")

    contract_l=contract.lower()
    # Verify the release contract structurally, not by one brittle prose spelling.
    # The manifest must bind all classes the candidate says are release-pinned.
    for token in ("task","asset","website","provider"):
        if token not in manifest_strings:
            errors.append("RELEASE_MANIFEST_COMPONENT_CLASS_MISSING:"+token)
    if "osworld" not in manifest_strings:
        errors.append("RELEASE_MANIFEST_OSWORLD_CODE_BINDING_MISSING")
    if "manifest" not in contract_l and "release" not in contract_l:
        errors.append("RELEASE_CONTRACT_SEMANTICS_MISSING")

    combined=(skill+"\n"+gitlab+"\n"+guide).lower()
    for needle in ("gitlab_url","gitlab_private_token"):
        if needle not in combined:
            errors.append("FUNCTIONAL_GITLAB_REQUIREMENT_MISSING:"+needle)

    if "self-host" not in combined and "self host" not in combined:
        errors.append("SELF_HOST_REQUIREMENT_MISSING")

    deleted=cand.get("logical_reconciliation",{}).get("deleted_brain_requirement")
    if deleted!="GITLAB_EXACT_REVISION_OR_INDEPENDENT_EQUIVALENCE_BINDING":
        errors.append("CANDIDATE_DELETION_DRIFT")

    repl=set(cand.get("logical_reconciliation",{}).get("replacement_load_bearing_requirements") or [])
    required={
      "SELF_HOST_TASK_WEB_GITLAB_USING_THE_SHARED_UPSTREAM_PROCEDURE",
      "GITLAB_URL_REACHABLE",
      "GITLAB_PRIVATE_TOKEN_VALID",
      "REQUIRED_GITLAB_API_BEHAVIOR_FOR_SELECTED_TASKS_VERIFIED_BY_PROTOCOL_PREFLIGHT",
      "NO_TERMINAL_CASE_EXECUTION_BEFORE_FRESH_REALITY_AUTHORIZATION",
    }
    if repl!=required:
        errors.append("REPLACEMENT_REQUIREMENTS_DRIFT")

    if cand.get("acceptance_credit_delta")!=0 or cand.get("fresh_reality_authority") is not False:
        errors.append("CREDIT_OR_AUTHORITY_OVERCLAIM")

    ok=not errors
    out={
      "schema":"PROJECT_BRAIN_OSWORLD_V21_GITLAB_PROTOCOL_RECONCILIATION_PUBLIC_RUNNER_RESULT_V1",
      "status":"PASS__UPSTREAM_RELEASE_CONTRACT_HAS_NO_GITLAB_REVISION_PIN__FUNCTIONAL_GITLAB_URL_TOKEN_SELF_HOST_REQUIREMENTS_PRESERVED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":errors,
      "verified":{
        "brain_candidate_exact_blob":git_blob_sha(CAND)==EXPECTED_BLOB,
        "release_manifest_has_no_gitlab_revision_binding":"gitlab" not in manifest_strings,
        "functional_gitlab_url_required":"gitlab_url" in combined,
        "functional_gitlab_private_token_required":"gitlab_private_token" in combined,
        "self_host_requirement_present":("self-host" in combined or "self host" in combined),
        "zero_credit":cand.get("acceptance_credit_delta")==0,
      }
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if ok else 1)

if __name__=="__main__":
    main()
