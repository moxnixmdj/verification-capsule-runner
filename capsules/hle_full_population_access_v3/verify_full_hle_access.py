#!/usr/bin/env python3
import json, urllib.request

URL="https://huggingface.co/api/datasets/cais/hle"
req=urllib.request.Request(URL,headers={"User-Agent":"project-brain-public-verifier/3.0"})
with urllib.request.urlopen(req,timeout=60) as resp:
    assert resp.status==200,resp.status
    meta=json.loads(resp.read())

assert meta.get("id")=="cais/hle",meta.get("id")
assert meta.get("gated")=="auto",meta.get("gated")
# Do not read gated benchmark case content. Repository metadata only.
print(json.dumps({
 "schema":"PROJECT_BRAIN_HLE_FULL_POPULATION_ACCESS_PUBLIC_RUNNER_RESULT_V3",
 "status":"PASS__CAIS_HLE_FULL_POPULATION_AUTO_GATE_CONFIRMED__ZERO_CASES",
 "dataset_id":meta.get("id"),
 "gated":meta.get("gated"),
 "terminal_cases_consumed":0,
 "new_reality_units_consumed":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0
},sort_keys=True))
