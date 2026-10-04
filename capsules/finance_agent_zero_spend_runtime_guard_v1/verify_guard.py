#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import zero_spend_provider_guard_v1 as g

def blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for group in ("candidate_blobs","authority_blobs"):
    for rel,expected in manifest[group].items():
        got=blob_sha(ROOT/rel)
        assert got==expected,(group,rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_V1.json").read_text())
intent=json.loads((ROOT/"canonical/action_intents/2026-10-04_FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_V1.json").read_text())
mass=json.loads((ROOT/"canonical/governance/FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_REDUCTION_20261004_V1.json").read_text())
massv=json.loads((ROOT/"canonical/verification/FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
v6=json.loads((ROOT/"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json").read_text())

assert gov["runtime"]["git_blob_sha"]==manifest["candidate_blobs"]["canonical/runtime/zero_spend_provider_guard_v1.py"]
assert gov["tests"]["git_blob_sha"]==manifest["candidate_blobs"]["canonical/tests/test_zero_spend_provider_guard_v1.py"]
assert gov["current_evidence"]["heldout_mass_git_blob_sha"]==manifest["authority_blobs"]["canonical/governance/FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_REDUCTION_20261004_V1.json"]
assert gov["current_evidence"]["heldout_mass_verification_git_blob_sha"]==manifest["authority_blobs"]["canonical/verification/FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
assert gov["current_evidence"]["root2_v6_frontier_git_blob_sha"]==manifest["authority_blobs"]["canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"]
assert intent["base_commit_sha"]==manifest["base_ref"]
assert mass["derived"]["scored_task_executions"]==1350
assert massv["verified"]["scored_task_executions"]==1350
assert "FINANCE_AGENT_V2_1350_EXECUTION_TAVILY_SEC_API_TIINGO_FREE_USAGE_FEASIBILITY" in v6["waiting_external_facts"]

def snap(provider="tavily", **kw):
    x={
      "provider_id":provider,
      "receipt_verified":True,
      "snapshot_fresh":True,
      "free_plan_active":True,
      "paid_fallback_enabled":False,
      "overage_enabled":False,
      "billing_charge_path_enabled":False,
      "incremental_spend_usd":0,
      "account_hash":"0123456789abcdef0123456789abcdef",
      "snapshot_hash":"fedcba9876543210fedcba9876543210",
    }
    x.update(kw)
    return x

def outcome(provider="tavily",call_id="c1",**kw):
    x={
      "provider_id":provider,
      "call_id":call_id,
      "paid_charge_observed":False,
      "quota_exhausted":False,
      "payment_required":False,
      "overage_observed":False,
      "observed_cost_usd":0,
    }
    x.update(kw)
    return x

def summary(provider,attempted=0,**kw):
    x={
      "provider_id":provider,
      "attempted_calls":attempted,
      "observed_calls":attempted,
      "all_calls_guarded":True,
      "guard_trip_count":0,
      "quota_exhaustion_count":0,
      "payment_required_count":0,
      "paid_charge_count":0,
      "observed_cost_usd":0,
    }
    x.update(kw)
    return x

# Adversarial fail-closed checks beyond the copied unit tests.
bad_snapshots=[
 {"receipt_verified":None},
 {"snapshot_fresh":None},
 {"free_plan_active":None},
 {"paid_fallback_enabled":None},
 {"overage_enabled":None},
 {"billing_charge_path_enabled":None},
 {"incremental_spend_usd":"0.0001"},
]
for bad in bad_snapshots:
    try:
        g.authorize_call(snap(**bad),provider_id="tavily",call_id="c1")
    except g.ZeroSpendBlocked:
        pass
    else:
        raise AssertionError(("BAD_ACCOUNT_STATE_AUTHORIZED",bad))

for bad in [
 {"quota_exhausted":None},
 {"payment_required":None},
 {"paid_charge_observed":None},
 {"overage_observed":None},
 {"observed_cost_usd":"0.0001"},
]:
    try:
        g.observe_call(snap(),provider_id="tavily",call_id="c1",outcome=outcome(**bad))
    except g.ZeroSpendBlocked:
        pass
    else:
        raise AssertionError(("BAD_CALL_OUTCOME_ACCEPTED",bad))

good=g.finalize_run(
    [summary("tavily",700),summary("sec_api",80),summary("tiingo",300)],
    required_provider_ids={"tavily","sec_api","tiingo"},
    evaluation_completed=True,
)
assert good["score_eligibility_zero_spend_gate"] is True
assert good["incremental_spend_usd"]==0
assert good["guard_trip_count"]==0

for bad_summaries in [
    [summary("tavily",1),summary("sec_api",1)],
    [summary("tavily",1,all_calls_guarded=False),summary("sec_api"),summary("tiingo")],
    [summary("tavily",2,observed_calls=1),summary("sec_api"),summary("tiingo")],
    [summary("tavily",1,quota_exhaustion_count=1),summary("sec_api"),summary("tiingo")],
    [summary("tavily",1,payment_required_count=1),summary("sec_api"),summary("tiingo")],
    [summary("tavily",1,paid_charge_count=1),summary("sec_api"),summary("tiingo")],
    [summary("tavily",1,observed_cost_usd="0.01"),summary("sec_api"),summary("tiingo")],
]:
    try:
        g.finalize_run(
            bad_summaries,
            required_provider_ids={"tavily","sec_api","tiingo"},
            evaluation_completed=True,
        )
    except g.ZeroSpendBlocked:
        pass
    else:
        raise AssertionError(("BAD_FULL_RUN_ACCEPTED",bad_summaries))

assert gov["accounting"]["incremental_spend_usd"]==0
assert gov["accounting"]["terminal_cases_consumed"]==0
assert gov["accounting"]["acceptance_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False
assert "NO_CLAIM_FREE_QUOTAS_ARE_SUFFICIENT_BEFORE_EXECUTION" in gov["hard_nonclaims"]

print(json.dumps({
  "schema":"PROJECT_BRAIN_FINANCE_AGENT_ZERO_SPEND_RUNTIME_GUARD_V1_PUBLIC_RUNNER_RESULT",
  "status":"PASS__EXACT_BLOBS__FAIL_CLOSED_ACCOUNT_AND_CALL_GUARD__FULL_RUN_ZERO_TRIP_ATTESTATION__NO_PRECLAIMED_QUOTA_SUFFICIENCY__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_candidate_and_authority_blobs":True,
    "current_v6_binding":True,
    "heldout_1350_binding":True,
    "unknown_or_paid_account_state_fails_closed":True,
    "quota_payment_overage_or_cost_event_fails_closed":True,
    "unobserved_or_unguarded_calls_fail_closed":True,
    "complete_zero_trip_zero_cost_run_can_pass_gate":True,
    "quota_sufficiency_not_preclaimed":True,
    "zero_terminal_credit":True
  }
},indent=2,sort_keys=True))
