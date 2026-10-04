#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, re, urllib.request, zipfile, io

ROOT=pathlib.Path(__file__).resolve().parent
SUBJ=ROOT/"subject/livebench_frozen_v1_forced_fail_20261004/LIVEBENCH_FROZEN_V1_FORCED_FAIL_PROOF_V1.json"
RUN_ID=37195688717
JOB_ID=111416950471
LOG_URL=f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/jobs/{JOB_ID}/logs"

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

proof=json.loads(SUBJ.read_text(encoding="utf-8"))
assert proof["schema"]=="PROJECT_BRAIN_LIVEBENCH_FROZEN_V1_FORCED_FAIL_PROOF_V1"
assert proof["frozen_candidate"]["adapter_v1_blob"]=="7e3885fa7a6e56df656c066e0a8f17cfa21424e7"
assert proof["additive_successor"]["adapter_v2_blob"]=="dbc895a0e458e411aafd3c96e0ddc2c01e657375"
assert proof["observed_replay"]["workflow_run_id"]==RUN_ID
assert proof["observed_replay"]["workflow_job_id"]==JOB_ID

# Independently fetch the public workflow job log and verify the one-use claim and exact sanitized histogram.
req=urllib.request.Request(LOG_URL,headers={"Accept":"application/vnd.github+json","User-Agent":"project-brain-independent-verifier"})
with urllib.request.urlopen(req,timeout=30) as resp:
    raw=resp.read()
# GitHub may return redirected raw text or zip-like bytes depending transport.
try:
    txt=raw.decode("utf-8-sig")
except UnicodeDecodeError:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        txt="\n".join(z.read(n).decode("utf-8","replace") for n in z.namelist())

assert "LIVEBENCH_V10_ATOMIC_CLAIM=" in txt
assert '"create_http_status": 201' in txt
m=re.search(r'LIVEBENCH_V8_STRUCTURAL_REFINEMENT=(\{.*\})',txt)
assert m, "missing structural refinement result"
obj=json.loads(m.group(1))
expected={
 "ARCHITECTURAL_GAP:CONTROL_OR_FANOUT":2,
 "COMPOSITION_PRODUCER:UNRESOLVED_GROUNDED_CLAUSES":27,
 "POLICY_BLOCK:POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN":43,
}
assert obj["classification_histogram"]==expected
assert obj["replayed_already_exposed_cases"]==72
assert obj["new_case_exposure"] is False
assert obj["unclassified_runtime_count"]==0
assert sum(expected.values())==72
assert "VALID_RESPONSE" not in expected

# Verify the additive V2 semantics from the exact source text pinned by public verifier history.
ADAPTER_URL="https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner/d784c3bff5f83672a6a1923fce00e395f3c5d413/canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py"
EXEC_URL="https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner/d784c3bff5f83672a6a1923fce00e395f3c5d413/execute_livebench_if_replay72_v4_candidate.py"
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"}),timeout=30) as r:
        return r.read()
adapter_bytes=get(ADAPTER_URL)
exec_bytes=get(EXEC_URL)
adapter_blob=hashlib.sha1(b"blob "+str(len(adapter_bytes)).encode()+b"\0"+adapter_bytes).hexdigest()
exec_blob=hashlib.sha1(b"blob "+str(len(exec_bytes)).encode()+b"\0"+exec_bytes).hexdigest()
assert adapter_blob=="dbc895a0e458e411aafd3c96e0ddc2c01e657375"
assert exec_blob=="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
adapter=adapter_bytes.decode()
executor=exec_bytes.decode()
assert "from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as fallback_v1" in adapter
assert "return fallback_v1.infer(request)" in adapter
assert 'if compiled.get("status")=="PASS" and compiled.get("semantic_seed_required") is False:' in adapter
assert 'if inf_err:' in executor
assert 'score,allok,n,followed,score_err=0.0,False' in executor

# Every observed case is a fallback/downstream blocker, so each receives zero in the frozen executor.
prefix_zero=72
population=200
remaining=population-prefix_zero
max_mass=remaining*1.0
threshold_mass=population*0.657
assert max_mass==128.0
assert threshold_mass==131.4
assert max_mass < threshold_mass
assert 100*max_mass/population==64.0

assert proof["arithmetic"]["full_population_score_upper_bound"]==128
assert proof["arithmetic"]["full_population_percent_upper_bound"]==64.0
assert proof["arithmetic"]["predicate_for_frozen_v1"]=="FAIL_FORCED"

print("PASS: exact frozen LiveBench V1 candidate is deductively below 65.7%; successor revisions are not covered")
