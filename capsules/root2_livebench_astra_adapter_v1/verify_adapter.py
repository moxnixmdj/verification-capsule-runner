#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

reg=json.loads((ROOT/"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json").read_text())
rows=[x for x in reg["adapters"] if x.get("benchmark_id")=="LIVEBENCH_IF_2026_06_25"]
assert len(rows)==1,rows
row=rows[0]
assert row["inference_capable"] is True
assert row["mode"]=="INFERENCE"
assert row["adapter_blob_sha"]==m["exact_brain_blobs"]["canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py"]

from canonical.runtime import astra_runtime
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter
from canonical.runtime import root2_external_task_entrypoint_v1 as ep

assert ep.preflight("LIVEBENCH_IF_2026_06_25")["inference_ready"] is True
assert ep.preflight("NOT_A_REAL_BENCHMARK")["inference_ready"] is False

request={
  "benchmark_id":"LIVEBENCH_IF_2026_06_25",
  "task_id":"synthetic-zero-case",
  "task_payload":{"instruction":"Synthetic integration probe."},
  "allowed_tools":[],
}

def model_independent_unstamped(step,mission):
    assert step["allow_optional_model_planner"] is False,step
    assert mission["mission_id"]=="ROOT2-LIVEBENCH-IF-INFERENCE"
    return {
      "adapter":"goal",
      "returncode":0,
      "stdout":"synthetic-answer",
      "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
      "trace":[{"synthetic":True}],
    }

with mock.patch.object(astra_runtime,"_run_goal_unstamped",side_effect=model_independent_unstamped):
    out=adapter.infer(request)
assert out["answer"]=="synthetic-answer",out
assert out["cognition_dependency_class"]=="MODEL_INDEPENDENT",out
assert out["model_dependency_count"]==0,out

def model_assisted_unstamped(step,mission):
    return {
      "adapter":"goal",
      "returncode":0,
      "stdout":"must-be-rejected",
      "controller_mode":"OPTIONAL_MODEL_ADVISORY",
      "planner_source":"synthetic",
      "trace":[],
    }

with mock.patch.object(astra_runtime,"_run_goal_unstamped",side_effect=model_assisted_unstamped):
    try:
        adapter.infer(request)
    except adapter.Root2InferenceBlocked as exc:
        assert "MODEL_DEPENDENCY_FORBIDDEN" in str(exc),exc
    else:
        raise AssertionError("MODEL_ASSISTED_RESULT_ACCEPTED")

bad=dict(request); bad["allowed_tools"]=["web_search"]
try:
    adapter.infer(bad)
except adapter.Root2InferenceBlocked as exc:
    assert "LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN" in str(exc),exc
else:
    raise AssertionError("EXTERNAL_TOOLS_ACCEPTED")

clean=json.loads((ROOT/"canonical/verification/ROOT2_LIVEBENCH_IF_ASTRA_ADAPTER_CLEANROOM_VERIFICATION_20261004_V1.json").read_text())
assert clean["test_result"]["passed"]==6
assert clean["test_result"]["failed"]==0
assert clean["terminal_cases_consumed"]==0
assert clean["acceptance_credit_delta"]==0

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT2_LIVEBENCH_ASTRA_ADAPTER_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_BLOBS__PUBLIC_RUNNER__REAL_RUN_GOAL_PROVENANCE_BOUNDARY__MODEL_ASSISTED_REJECTED__ZERO_CASE__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_brain_blob_identities":True,
    "registry_inference_binding":True,
    "entrypoint_preflight":True,
    "real_astra_run_goal_provenance_boundary":True,
    "model_independent_result_accepted":True,
    "model_assisted_result_rejected":True,
    "external_tools_rejected":True,
    "cleanroom_6_of_6_bound":True
  },
  "limitations":[
    "SYNTHETIC_INTEGRATION_STUBS_ONLY_THE_INTERNAL_UNSTAMPED_TASK_EXECUTION",
    "NO_LIVEBENCH_CASE_CONTENT_READ",
    "NO_LIVEBENCH_SCORE_PRODUCED",
    "DOES_NOT_PROVE_65_7_THRESHOLD"
  ],
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False
},indent=2,sort_keys=True))
