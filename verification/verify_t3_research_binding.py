import hashlib,json
from pathlib import Path

p=Path("verification/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
raw=p.read_bytes()
# Git blob object hash, to bind exact canonical Brain bytes.
git_blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
assert git_blob=="547a709fa1000cf2e5ee9294397eeae2c48685ac",git_blob
j=json.loads(raw)
assert j["schema"]=="PROJECT_BRAIN_T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1"
assert j["portfolio"]=="T3"
assert j["behavior_id"]=="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001"
assert j["execution_authority"] is False
assert j["terminal_results_observed"]==0
assert j["fresh_terminal_evidence_consumed"]==0
assert j["incremental_spend_usd"]==0
s={x["id"]:x for x in j["public_surfaces"]}
h=s["HLE_WITH_TOOLS"]
assert h["target_percent"]==67.7
assert h["canonical_population_count"]==2500
assert h["official_source_commit"]=="22ed3074b1e7b134bcbc09028d0ba320839b0655"
assert h["dataset_repository_sha"]=="5a81a4c7271a2a2a312b9a690f0c2fde837e4c29"
assert h["dataset_content_access"].startswith("GATED")
assert h["anonymous_terminal_execution"] is False
assert h["scorer_blob_sha"]=="d30882400982c058f1130b82af790b197767a091"
assert h["paid_judge_required"] is False
t=s["TERMINAL_BENCH_SCIENCE_0_1"]
assert t["target_percent"]==58.7
assert t["source_tag"]=="v0.1.0"
assert t["source_commit"]=="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
assert t["harbor_dataset_revision"]==10
assert t["harbor_dataset_content_hash"]=="sha256:91531bf50016a7c64f6cc60794a17c64c6b2c14858a8ae0de39ca16f2abd611a"
assert "NO_POST_HOC_CASE_REPLACEMENT" in t["resource_fail_rule"]
g=j["prewave_execution_gates"]
assert g["HLE_CANONICAL_CONTENT_ACCESS_AT_ZERO_INCREMENTAL_SPEND"]=="OPEN_GATED_ACCESS_DEPENDENCY"
assert g["HLE_STRICT_SCORER_INDEPENDENTLY_VERIFIED"] is True
assert g["HLE_CANONICAL_POPULATION_METADATA_FROZEN"] is True
assert g["TB_SCIENCE_V0_1_DATASET_IDENTITY_FROZEN"] is True
assert g["TB_SCIENCE_ZERO_COST_LOCAL_DOCKER_HARBOR_CARRIER_FROZEN"] is True
assert g["TERMINAL_CASES_EXPOSED"]==0
assert j["information_boundary"]["candidate_receives_reference_answer"] is False
assert j["information_boundary"]["candidate_receives_hidden_oracle"] is False
assert j["terminal_acceptance"]["post_result_tuning"] is False
print("T3_RESEARCH_BINDING_PUBLIC_VERIFICATION_PASS")
