#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parent
PROD=ROOT/"execute_livebench_if_frozen_20261004.py"
WF=ROOT/".github/workflows/execute-livebench-if-frozen-20261004.yml"

def blob(p):
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

src=PROD.read_text(encoding="utf-8")
wf=WF.read_text(encoding="utf-8")
ast.parse(src)
assert 'branches: ["execute/livebench-if-frozen-20261004"]' in wf
assert 'paths: ["EXECUTE_LIVEBENCH_IF_FROZEN_20261004"]' in wf
assert "pull_request:" not in wf
assert 'python-version: "3.12.14"' in wf
assert "ubuntu-24.04" in wf
assert "actions/upload-artifact@v4" in wf
assert "TARGET_COUNT=200" in src
assert "TARGET_THRESHOLD=65.7" in src
assert 'TARGET_RELEASE="2026-06-25"' in src
assert 'adaptive_case_selection":False' in src
assert 'case_replacement":False' in src
assert 'terminal_case_tuning":False' in src
assert 'paid_external_model_or_api_used":False' in src
assert 'incremental_spend_usd":0' in src
assert 'promotion_authority":False' in src
assert 'acceptance_credit_delta":0' in src
assert "active.sort(" in src
assert "for idx,row in enumerate(active):" in src
assert "len(active)!=TARGET_COUNT" in src
assert "NONEMPTY_SYSTEM_PROMPT_UNSUPPORTED" in src
assert "UNSUPPORTED_TURN_SHAPE" in src
assert 'BLOBS={' in src and 'SCORER_BLOBS={' in src
assert 'subject/livebench_direct_authority_activation_v1/activation.json' in src
assert '08929577573866dc2bead65a19a856a6b4e152d2' in src
assert 'a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25' in src
assert '8f8e5c381a16e3f24257776edd53471fe86f8091' in src
assert '8ce01747887ec0792c8f024e1972e34ece781676' in src
# No network/model provider calls may exist in candidate source.
for forbidden in ["openai","anthropic","litellm","api_key","temperature=","random.shuffle","random.sample"]:
    assert forbidden not in src.lower(), forbidden
# Runtime verifier must run before terminal parquet download.
assert src.index("pre=point_of_use_preflight()") < src.index("urllib.request.urlopen(DATASET_URL")
# Full population must be established before first inference.
assert src.index("if len(active)!=TARGET_COUNT") < src.index("for idx,row in enumerate(active):")
print(json.dumps({
  "status":"PASS",
  "production_script_git_blob_sha":blob(PROD),
  "production_workflow_git_blob_sha":blob(WF),
  "terminal_case_content_read":False,
  "terminal_cases_consumed":0,
  "execution_trigger_inert_on_pull_request":True,
  "production_population_count":200,
  "adaptive_case_selection":False,
  "case_replacement":False,
  "terminal_case_tuning":False,
  "acceptance_credit_delta":0,
},sort_keys=True))
