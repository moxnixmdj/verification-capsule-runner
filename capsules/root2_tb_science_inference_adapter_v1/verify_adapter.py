#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

registry=json.loads((ROOT/"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json").read_text())
rows=[x for x in registry["adapters"] if x.get("benchmark_id")=="TERMINAL_BENCH_SCIENCE_0_1"]
assert len(rows)==1,rows
row=rows[0]
assert row["mode"]=="INFERENCE",row
assert row["inference_capable"] is True,row
assert row["adapter_blob_sha"]==manifest["exact_brain_blobs"]["canonical/runtime/root2_tb_science_inference_adapter_v1.py"],row
assert row["controller_blob_sha"]=="5557efd21f1a433ad16766def3775a79c459784b",row
assert row["model_dependency_count"]==1,row
assert row["model_has_terminal_authority"] is False,row

gov=json.loads((ROOT/"canonical/governance/ROOT2_TB_SCIENCE_INFERENCE_ADAPTER_CANDIDATE_V1.json").read_text())
assert gov["candidate_effect"]["root2_generic_inference_adapter_count_before"]==0
assert gov["candidate_effect"]["root2_generic_inference_adapter_count_after_if_verified"]==1
assert gov["candidate_effect"]["terminal_case_content_read"]==0
assert gov["candidate_effect"]["terminal_results_observed"]==0
assert gov["candidate_effect"]["score_produced"] is False
assert gov["candidate_effect"]["acceptance_closed"] is False
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta","new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd"):
    assert gov[k]==0,(k,gov[k])
for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
    assert gov[k] is False,(k,gov[k])

from canonical.runtime import root2_tb_science_inference_adapter_v1 as adapter
req={
  "benchmark_id":adapter.BENCHMARK_ID,
  "task_id":"synthetic",
  "task_payload":{"instruction":"synthetic task"},
  "allowed_tools":["environment_exec","finish"],
  "environment":None,
  "output_contract":{"type":"text"},
  "brain_commit":"deadbeef",
  "configuration_hash":"cfg",
  "tool_policy_hash":"policy",
}
try:
    adapter.infer(req)
except adapter.TBScienceAdapterBlocked as exc:
    assert "LIVE_HARBOR_ENVIRONMENT_REQUIRED" in str(exc),exc
else:
    raise AssertionError("MISSING_ENVIRONMENT_DID_NOT_FAIL_CLOSED")

bad=dict(req); bad["environment"]=object(); bad["allowed_tools"]=["environment_exec","network"]
try:
    adapter.infer(bad)
except adapter.TBScienceAdapterBlocked:
    pass
else:
    raise AssertionError("UNSUPPORTED_TOOL_DID_NOT_FAIL_CLOSED")

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT2_TB_SCIENCE_INFERENCE_ADAPTER_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_BLOBS__FIRST_INFERENCE_ADAPTER__FAIL_CLOSED__ZERO_CASE__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_brain_blob_identities":True,
    "registry_inference_binding":True,
    "existing_controller_content_binding":True,
    "model_dependency_declared":True,
    "model_has_terminal_authority_false":True,
    "missing_environment_fail_closed":True,
    "unsupported_tools_fail_closed":True,
    "zero_case":True,
    "zero_credit":True
  },
  "new_reality_units_consumed":0,
  "terminal_cases_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False
},indent=2,sort_keys=True))
