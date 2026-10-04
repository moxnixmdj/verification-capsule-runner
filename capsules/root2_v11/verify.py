from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

BASE=Path("capsules/root2_v11")
EXPECTED={
  "v10.json":"2012926814d0d06405da56da64e589b06fef1756",
  "v11.json":"6857750dea3a0af48a5acc545b6f66b619d4335b",
  "finance.json":"2a831b8632b18fe9e10ed423f131b6ae93d99b77",
  "osworld.json":"d03a0a6d85148017c073b79ee78895cc94870eb3",
  "osworld_verification.json":"ca58b9e09b2e0fa24d7c5781e93c55a6d46e2935",
}

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch_json(url:str):
    req=urllib.request.Request(url,headers={"User-Agent":"Project-Brain-Independent-Verifier","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode())

for n,h in EXPECTED.items():
    got=blob(BASE/n)
    assert got==h,(n,h,got)

v10=json.loads((BASE/"v10.json").read_text())
v11=json.loads((BASE/"v11.json").read_text())
fin=json.loads((BASE/"finance.json").read_text())
osw=json.loads((BASE/"osworld.json").read_text())
oswv=json.loads((BASE/"osworld_verification.json").read_text())

assert v11["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11"
assert v11["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert v11["source_bindings"]["prior_frontier_v10"]["git_blob_sha"]==EXPECTED["v10.json"]
assert v11["source_bindings"]["finance_index_public_transform_saturation"]["git_blob_sha"]==EXPECTED["finance.json"]
assert v11["source_bindings"]["osworld_gitlab_sept10_public_state"]["git_blob_sha"]==EXPECTED["osworld.json"]
assert v11["source_bindings"]["osworld_gitlab_sept10_public_state"]["verification_git_blob_sha"]==EXPECTED["osworld_verification.json"]

assert v11["exact_state"]==v10["exact_state"]
assert v11["exact_state"]=={
  "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
  "root1_positive_gap_count":0,"root2_only_count":16,"root3_only_count":7,
  "root2_and_root3_count":3,"root2_touching_predicates":19
}
assert v11["waiting_external_facts"]==v10["waiting_external_facts"]
assert v11["fresh_reality_preserved_not_authorized"]==v10["fresh_reality_preserved_not_authorized"]
assert v11["tb4_carrier_portfolio"]==v10["tb4_carrier_portfolio"]
assert v11["finance_agent_v2_zero_spend_route"]==v10["finance_agent_v2_zero_spend_route"]
assert v11["finance_agent_v2_dual_route"]==v10["finance_agent_v2_dual_route"]

old=set(v10["runnable_zero_reality"])
new=set(v11["runnable_zero_reality"])
assert "OSWORLD_GATED_ASSET_ACCESS_AND_END_TO_END_PROTOCOL_EQUIVALENCE" in old
assert "OSWORLD_GATED_ASSET_ACCESS_AND_END_TO_END_PROTOCOL_EQUIVALENCE" not in new
assert "OSWORLD_GATED_ASSET_ACCESS_PLUS_ANTHROPIC_GITLAB_IDENTITY_OR_PROTOCOL_EQUIVALENCE_AGAINST_FROZEN_SEPT10_PUBLIC_CANDIDATE" in new
assert "FINANCE_INDEX_MINIMIZE_VERIFIED_NORMALIZED_WEIGHTED_LOWER_BOUND_DEFICIT_TO_61" in old
assert "FINANCE_INDEX_MINIMIZE_VERIFIED_NORMALIZED_WEIGHTED_LOWER_BOUND_DEFICIT_TO_61" not in new
assert "FINANCE_INDEX_OWNER_RESULT_OR_VERIFIED_COMPONENT_LOWER_BOUNDS_ONLY__PUBLIC_INNER_TRANSFORM_SEARCH_SATURATED" in new

assert len(v11["projection_deltas"])==len(v10["projection_deltas"])+2
dels={d["deletion"] for d in v11["projection_deltas"][len(v10["projection_deltas"]):]}
assert dels=={
  "REPEAT_GENERIC_PUBLIC_FINANCE_INNER_TRANSFORM_SEARCH_AND_DUPLICATE_OWNER_OUTREACH",
  "GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY_SEARCH",
}

routes={x["route"]:x for x in v11["exhausted_or_deleted"]}
assert routes["FINANCE_INDEX_GENERIC_PUBLIC_INNER_TRANSFORM_SEARCH"]["state"].startswith("SATURATED")
assert routes["OSWORLD_GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY"]["state"].startswith("DELETED")

assert fin["exact_deduction"]["public_free_api_documented_inner_capability_transform"] is False
assert fin["exact_deduction"]["finance_subscore_zero_floor_proved"] is False
assert osw["public_state"]["latest_commit_at_or_before_2026_09_10"]=="8655d651722f4254e59e813de9f68a6732ea525c"
assert oswv["verified"]["anthropic_exact_revision_identity_proved"] is False

finance_run=fetch_json("https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/37174229191")
assert finance_run["conclusion"]=="success"
finance_pr=fetch_json("https://api.github.com/repos/moxnixmdj/verification-capsule-runner/pulls/1656")
assert finance_pr["merged"] is True

assert v11["execution_authority"] is False
assert v11["promotion_authority"] is False
assert v11["fresh_reality_authority"] is False
assert v11["accounting"]["incremental_spend_usd"]==0
assert v11["accounting"]["new_reality_units_consumed"]==0
assert v11["accounting"]["terminal_cases_consumed"]==0
assert v11["accounting"]["acceptance_credit_delta"]==0

print("ROOT2_V11_FINANCE_OSWORLD_COMPRESSION_PASS__COUNTS_STABLE__ZERO_CREDIT__NO_FRESH_REALITY")
