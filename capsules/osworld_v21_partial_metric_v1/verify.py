#!/usr/bin/env python3
import hashlib,json,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def gitblob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

exp=json.loads((ROOT/"EXPECTED.json").read_text())
candidate=(ROOT/"OSWORLD_V21_PARTIAL_METRIC_SEMANTICS_RECONCILIATION_V1.json").read_bytes()
assert gitblob(candidate)==exp["brain_candidate_blob"]
c=json.loads(candidate)
assert c["target_predicate"]=="OSWORLD_2_1_PARTIAL_GE_81_8"
assert c["proved_narrow_conclusion"]["delete_interpretation"]=="PARTIAL_MEANS_AN_UNIDENTIFIED_TASK_SUBSET"
assert c["proved_narrow_conclusion"]["replacement"]=="PARTIAL_IS_A_REWARD_OR_SCORING_QUALIFIER"
assert c["proved_narrow_conclusion"]["anthropic_exact_run_population"]=="OPEN"
assert "NO_CLAIM_ANTHROPIC_EVALUATED_ALL_108_TASKS" in c["hard_nonclaims"]
assert c["terminal_cases_consumed"]==0 and c["incremental_spend_usd"]==0
assert c["acceptance_credit_delta"]==0 and c["fresh_reality_authority"] is False

manifest=get("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/benchmark_releases/osworld-v2.1.json")
assert gitblob(manifest)==exp["osworld_manifest_blob"]
m=json.loads(manifest)
assert m["release"]=="osworld-v2.1"
assert m["task_hash_manifest"]["task_count"]==exp["task_count"]
assert m["tasks"]["commit"]==exp["tasks_revision"]

metric=get("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/osworld-v2.1/desktop_env/evaluators/metrics/basic_os.py")
assert gitblob(metric)==exp["osworld_metric_blob"]
txt=metric.decode()
assert "partial_reward (bool, default False) - enable partial scoring" in txt
assert "With partial_reward=True: score in [0.0, 1.0]" in txt

print(json.dumps({
 "schema":"PROJECT_BRAIN_OSWORLD_V21_PARTIAL_METRIC_PUBLIC_RUNNER_RESULT_V1",
 "status":"PASS__EXACT_PRIMARY_BLOBS__108_TASK_RELEASE__PARTIAL_REWARD_IS_SCORING_MODE__UNKNOWN_ANTHROPIC_POPULATION_PRESERVED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
