from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/H100_LEXICAL_SOURCE_FALLBACK_KNOWLEDGE_V1.json":"fe50744543f7c4c5ffe1a8d1d4855568a868df80",
 "canonical/governance/H100_LEXICAL_SOURCE_FALLBACK_PREEXPOSURE_V1.json":"86e39332746383b4f8a8169018b341006bd9d362",
 "canonical/runtime/h100_lexical_source_fallback_v1.py":"3980b1066058c77e515bd3b82b31a0f1298415f2",
 "canonical/tests/test_h100_lexical_source_fallback_v1.py":"6b59aacf8fbd687744e828bf07f546f9db6bca53",
}
FORBIDDEN_RUNTIME_TERMS=("covariate","regressor")

def blob_sha(data:bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def load_runtime():
    p=ROOT/"canonical/runtime/h100_lexical_source_fallback_v1.py"
    spec=importlib.util.spec_from_file_location("h100_source_fallback",p)
    if spec is None or spec.loader is None:
        raise SystemExit("IMPORT_SPEC_FAILED")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def fetch_text(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 H100-verifier"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        raw=resp.read().decode("utf-8","ignore")
    raw=html.unescape(raw)
    raw=re.sub(r"<[^>]+>"," ",raw)
    return " ".join(raw.lower().split())

def verify_sources(knowledge):
    by_term={r["term"]:r for r in knowledge["records"]}
    cov=by_term["covariate"]
    reg=by_term["regressor"]
    cov_text=fetch_text(cov["source_url"])
    reg_text=fetch_text(reg["source_url"])
    if "covariate" not in cov_text or "explanatory variable" not in cov_text:
        raise SystemExit("COVARIATE_SOURCE_RELATION_NOT_CONFIRMED")
    if "regressor" not in reg_text:
        raise SystemExit("REGRESSOR_SOURCE_TERM_NOT_CONFIRMED")
    if not all(p in reg_text for p in ("independent variable","predictor","explanatory variable")):
        raise SystemExit("REGRESSOR_SOURCE_RELATION_NOT_CONFIRMED")

def main():
    for rel,expected in EXPECTED.items():
        actual=blob_sha((ROOT/rel).read_bytes())
        if actual!=expected:
            raise SystemExit(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")

    runtime_text=(ROOT/"canonical/runtime/h100_lexical_source_fallback_v1.py").read_text().lower()
    for term in FORBIDDEN_RUNTIME_TERMS:
        if term in runtime_text:
            raise SystemExit("TERM_HARDCODED_IN_RUNTIME:"+term)

    knowledge=json.loads((ROOT/"canonical/governance/H100_LEXICAL_SOURCE_FALLBACK_KNOWLEDGE_V1.json").read_text())
    pre=json.loads((ROOT/"canonical/governance/H100_LEXICAL_SOURCE_FALLBACK_PREEXPOSURE_V1.json").read_text())
    verify_sources(knowledge)
    if len(pre["tasks"])!=2:
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")

    mod=load_runtime()
    for task in pre["tasks"]:
        records=[r for r in knowledge["records"] if r["term"]==task["term"]]
        out=mod.resolve_source_relations(task["term"],records)
        if out["status"]!=task["expected_status"] or out["role"]!=task["expected_role"]:
            raise SystemExit("PREEXPOSURE_MISMATCH:"+task["task_id"])
        if out["persistent_learned_bytes"]!=0:
            raise SystemExit("LEARNED_BYTES_NONZERO")
        if out["external_frontier_model_calls"]!=0 or out["external_learned_capability_calls"]!=0:
            raise SystemExit("EXTERNAL_LEARNED_PROVIDER_USED")

    fresh_input=mod.resolve_source_relations("fresh_alpha",[
      {"term":"fresh_alpha","source_id":"fresh-a","relation_phrases":["predictor variable"]}
    ])
    if fresh_input["status"]!="ROLE_IDENTIFIED" or fresh_input["role"]!="INPUT":
        raise SystemExit("FRESH_INPUT_RELATION_CHALLENGE_FAILED")

    fresh_target=mod.resolve_source_relations("fresh_beta",[
      {"term":"fresh_beta","source_id":"fresh-b","relation_phrases":["response variable"]}
    ])
    if fresh_target["status"]!="ROLE_IDENTIFIED" or fresh_target["role"]!="TARGET":
        raise SystemExit("FRESH_TARGET_RELATION_CHALLENGE_FAILED")

    conflict=mod.resolve_source_relations("fresh_gamma",[
      {"term":"fresh_gamma","source_id":"fresh-c1","relation_phrases":["predictor variable"]},
      {"term":"fresh_gamma","source_id":"fresh-c2","relation_phrases":["response variable"]}
    ])
    if conflict["status"]!="ABSTAIN_SOURCE_ROLE_CONFLICT" or conflict["role"] is not None:
        raise SystemExit("FRESH_CONFLICT_CHALLENGE_FAILED")

    print(json.dumps({
      "status":"PASS",
      "exact_subject_blobs":True,
      "live_source_relation_checks":"2_OF_2_PASS",
      "observed_missing_terms_repaired":"2_OF_2",
      "fresh_input_relation_challenge":"PASS",
      "fresh_target_relation_challenge":"PASS",
      "fresh_conflict_challenge":"PASS",
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "hard_nonclaim":"TWO_TERM_SOURCE_FALLBACK_PASS_IS_NOT_OPEN_WORLD_LEXICAL_COVERAGE"
    },sort_keys=True))

if __name__=="__main__":
    main()
