#!/usr/bin/env python3
import json, urllib.request

META="https://huggingface.co/api/datasets/cais/hle-diamond"
CARD="https://huggingface.co/datasets/cais/hle-diamond/raw/main/README.md"

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        assert r.status==200,(url,r.status)
        return r.read()

meta=json.loads(get(META))
assert meta.get("id")=="cais/hle-diamond",meta.get("id")
gated=meta.get("gated")
assert gated in (False,None),("unexpected_gated_state",gated)

card=get(CARD).decode("utf-8","replace")
assert 'load_dataset("cais/hle-diamond", split="test")' in card
assert "HLE-Diamond consists of 1,000 questions" in card

# Metadata and dataset card only. No task rows are downloaded or read.
print(json.dumps({
  "schema":"PROJECT_BRAIN_HLE_DIAMOND_PUBLIC_ACCESS_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__ANONYMOUS_METADATA_AND_CARD_ACCESS__NOT_GATED__TEST_SPLIT_ADVERTISED__ZERO_CASES_READ",
  "dataset_id":meta.get("id"),
  "gated":gated,
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0
},sort_keys=True))
