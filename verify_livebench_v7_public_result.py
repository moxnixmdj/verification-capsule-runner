#!/usr/bin/env python3
from __future__ import annotations
import json, os, urllib.request, urllib.error

REPO="moxnixmdj/verification-capsule-runner"
RUN_ID=37193519638
JOB_ID=111410499196
HEAD_SHA="e5e2a97bfeb2d95839917e01281526c1770a499c"
CLAIM_REF="refs/heads/livebench-v7-claims/5ea710ae6d8b64c9ae990da5bd3ae747806e12843b8c2566bbb1be83d09ab53d"
ACTIVATION_BLOB="e394a1bf48de226c184617980e513e98137ca9ff"
EXPECTED_HIST={
 "POLICY_BLOCK:POST_PROMPT_ACQUISITION_OR_NETWORK_FORBIDDEN":43,
 "STATIC_BLOCKER:BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED":27,
 "STATIC_BLOCKER:GOAL_ARCHITECTURAL_GAP":2,
}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None

def headers():
    t=os.environ.get("GITHUB_TOKEN","")
    return {"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",**({"Authorization":"Bearer "+t} if t else {})}

def api(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers()),timeout=60) as r: return r.read()

def logs(url):
    op=urllib.request.build_opener(NoRedirect)
    try:
        with op.open(urllib.request.Request(url,headers=headers()),timeout=60) as r: return r.read()
    except urllib.error.HTTPError as e:
        assert e.code in (301,302,303,307,308),e.code
        loc=e.headers["Location"]
        with urllib.request.urlopen(urllib.request.Request(loc,headers={"User-Agent":"project-brain-verifier"}),timeout=60) as r: return r.read()

run=json.loads(api(f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}"))
assert run["head_sha"]==HEAD_SHA
assert run["status"]=="completed"
assert run["conclusion"]=="failure" # only later persistence step failed
jobs=json.loads(api(f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}/jobs?per_page=100"))["jobs"]
job=[j for j in jobs if int(j["id"])==JOB_ID][0]
steps={s["name"]:s for s in job["steps"]}
assert steps["Verify exact V7 bytes"]["conclusion"]=="success"
assert steps["Point-of-use zero-case verification"]["conclusion"]=="success"
assert steps["Atomic claim and sanitized replay72 classification"]["conclusion"]=="success"
assert steps["Persist immutable V7 evidence"]["conclusion"]=="failure"
raw=logs(f"https://api.github.com/repos/{REPO}/actions/jobs/{JOB_ID}/logs").decode("utf-8","replace")
claim=[];diag=[]
for line in raw.splitlines():
    if "LIVEBENCH_V7_ATOMIC_CLAIM=" in line: claim.append(json.loads(line.split("LIVEBENCH_V7_ATOMIC_CLAIM=",1)[1]))
    if "LIVEBENCH_V7_SANITIZED_DIAGNOSTIC=" in line: diag.append(json.loads(line.split("LIVEBENCH_V7_SANITIZED_DIAGNOSTIC=",1)[1]))
assert len(claim)==1 and len(diag)==1
c=claim[0]; d=diag[0]
assert c["claim_ref"]==CLAIM_REF
assert c["create_http_status"]==201
assert c["response_object_sha"]==HEAD_SHA
assert c["terminal_dataset_read_before_claim"] is False
assert c["execution_started_before_claim"] is False
assert d["activation_blob_sha"]==ACTIVATION_BLOB
assert d["classification_histogram"]==EXPECTED_HIST
assert d["replay_prefix_limit"]==72 and d["terminal_cases_consumed"]==72
assert d["new_case_exposure"] is False
assert d["valid_response_count"]==0 and d["unclassified_runtime_count"]==0
assert d["case_ids_emitted"] is False and d["prompt_text_emitted"] is False and d["response_text_emitted"] is False and d["raw_exception_text_emitted"] is False
print(json.dumps({
 "schema":"PROJECT_BRAIN_LIVEBENCH_V7_RESULT_PUBLIC_RECOMPUTATION_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
 "claim_http_201":True,
 "authoritative_head_sha":HEAD_SHA,
 "histogram":EXPECTED_HIST,
 "valid_response_count":0,
 "unclassified_runtime_count":0,
 "replayed_already_exposed_cases":72,
 "new_case_exposure":False,
 "persistence_failure_after_semantic_result":True,
 "acceptance_credit_delta":0
},sort_keys=True))
