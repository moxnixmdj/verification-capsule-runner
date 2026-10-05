#!/usr/bin/env python3
import hashlib, json, sys, urllib.request
from pathlib import Path

PINNED_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
EXPECTED_BLOBS={
 "livebench/common.py":"95373cc6a82bc935013e2c23d2a183022f802f5c",
 "livebench/if_runner/ifbench/evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
 "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
 "livebench/if_runner/ifbench/instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
}
EXPECTED_HF_HEAD="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
EXPECTED_HF_DATE_PREFIX="2025-04-07"

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

root=Path(sys.argv[1])
src={}
for rel,sha in EXPECTED_BLOBS.items():
    data=(root/rel).read_bytes()
    got=git_blob(data)
    assert got==sha,(rel,got,sha)
    src[rel]=data.decode("utf-8")

common=src["livebench/common.py"]
evaluation=src["livebench/if_runner/ifbench/evaluation_lib.py"]
scorer=src["livebench/process_results/instruction_following/utils.py"]
instructions=src["livebench/if_runner/ifbench/instructions.py"]

# The pinned runner resolves category data from the mutable HF repo and supplies no revision.
assert 'load_dataset(f"{LIVE_BENCH_HF_ORGANIZATION}/{dataset_name}", split=split)' in common
assert "revision=" not in common[common.index("def get_hf_dataset"):common.index("def get_tasks_from_hf_category")]

# Strict grading consumes stored hidden kwargs; it does not infer them from visible prompt.
assert "instruction.build_description(**inp.kwargs[index])" in evaluation
assert "kwargs=question['kwargs']" in scorer
assert "prompt=question['turns'][0]" in scorer

# Pin the two hidden-state-dependent checker semantics.
assert "nltk.ngrams(value, n)" in instructions
assert "nltk.ngrams(self._reference_text, n)" in instructions
assert "self._prompt_to_repeat.strip().lower().split()[self._n_start:self._n_end]" in instructions

# Executable non-identifiability witnesses.
def repeat_span(prompt, start, end, response):
    return response.strip().lower().split()==prompt.strip().lower().split()[start:end]
visible_repeat={"n_start":0,"n_end":1}
response_repeat="alpha"
assert repeat_span("alpha rest",0,1,response_repeat)
assert not repeat_span("beta rest",0,1,response_repeat)

def trigram_set(s):
    return {tuple(s[i:i+3]) for i in range(max(0,len(s)-2))}
def overlap_pass(reference, percentage, response):
    ng=trigram_set(response)
    assert ng
    rg=trigram_set(reference)
    overlap=len(ng & rg)/len(ng)
    return percentage-2 <= overlap*100 <= percentage+2
visible_overlap={"percentage":100}
response_overlap="abcdef"
assert overlap_pass("abcdef",100,response_overlap)
assert not overlap_pass("uvwxyz",100,response_overlap)

# Independent current public-source boundary check. Fail closed if the mutable source changes.
req=urllib.request.Request(
    "https://huggingface.co/api/datasets/livebench/instruction_following/commits/main",
    headers={"User-Agent":"project-brain-independent-verifier/1"},
)
with urllib.request.urlopen(req,timeout=30) as r:
    commits=json.load(r)
assert commits and isinstance(commits,list)
head=commits[0]
head_id=head.get("id") or head.get("commit_id")
head_date=str(head.get("createdAt") or head.get("created_at") or head.get("date") or "")
assert head_id==EXPECTED_HF_HEAD,(head_id,EXPECTED_HF_HEAD)
assert head_date.startswith(EXPECTED_HF_DATE_PREFIX),(head_date,EXPECTED_HF_DATE_PREFIX)

receipt={
 "schema":"LIVEBENCH_IFBENCH58_PUBLIC_PROVENANCE_BOUNDARY_INDEPENDENT_VERIFIER_V1",
 "status":"PASS",
 "pinned_livebench_commit":PINNED_COMMIT,
 "blob_sha":EXPECTED_BLOBS,
 "hf_public_head_observed":head_id,
 "hf_public_head_date":head_date,
 "checks":{
   "runner_uses_unrevisioned_hf_category_load":True,
   "strict_evaluator_consumes_stored_kwargs":True,
   "repeat_span_visible_state_nonidentifiability_witness":True,
   "ratio_overlap_visible_state_nonidentifiability_witness":True,
 },
 "terminal_rows_read":0,
 "terminal_kwargs_read":0,
}
Path("livebench_ifbench58_public_provenance_boundary_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
