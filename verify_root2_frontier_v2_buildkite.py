import hashlib, json, pathlib, re, urllib.request

FILES = {
  "carrier": "subject/TB4_BUILDKITE_ALL_ACCESS_TRIAL_CARRIER_CANDIDATE_20261004_V1.json",
  "frontier": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2.json",
}
EXPECTED = {
  "carrier": "2725cf6820fb7ce6025213d474b9acf2937282ee",
  "frontier": "36013ab1768260cca9dca4dbe1aa11a68dab56cf",
}

def git_blob_sha(path):
    b=pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for k,p in FILES.items():
    got=git_blob_sha(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

carrier=json.loads(pathlib.Path(FILES["carrier"]).read_text())
frontier=json.loads(pathlib.Path(FILES["frontier"]).read_text())

env=carrier["frozen_minimum_envelope"]
assert env["cpus_at_least"]==8
assert env["usable_memory_mb_at_least"]==16384
assert env["free_storage_mb_at_least"]==51200
assert env["docker_required"] is True and env["docker_compose_required"] is True
assert carrier["narrow_conclusion"]["tb4_carrier_admissibility_proved"] is False
assert carrier["execution_authority"] is False
assert carrier["promotion_authority"] is False
assert carrier["fresh_reality_authority"] is False
assert carrier["incremental_spend_usd"]==0
assert "NO_TB4_CARRIER_PROMOTION_FROM_PROVIDER_DOCUMENTATION_ALONE" in frontier["hard_rules"]

s=[x for x in frontier["verified_or_primary_source_deltas"] if x["target"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
assert len(s)==1
assert s[0]["remaining"]==["metric:matched_quality","matched_quality_noninferiority"]
assert s[0]["delete"]=="required_claim_coverage_noninferiority"
t=[x for x in frontier["verified_or_primary_source_deltas"] if x["target"]=="CODING_TB4_GE_66_4"]
assert len(t)==1 and "BUILDKITE" in t[0]["replace_with"]
assert frontier["fresh_reality_authority"] is False
assert frontier["accounting"]["incremental_spend_usd"]==0

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","ignore")

linux=fetch("https://buildkite.com/docs/agent/buildkite-hosted/linux")
pricing=fetch("https://www.buildkite.com/pricing/")
linux_text=re.sub(r"<[^>]+>"," ",linux)
pricing_text=re.sub(r"<[^>]+>"," ",pricing)
linux_text=re.sub(r"\s+"," ",linux_text)
pricing_text=re.sub(r"\s+"," ",pricing_text)

for token in ["LINUX_AMD64_8X32","8","32 GB","158 GB","docker","docker-compose"]:
    assert token.lower() in linux_text.lower(), token
for token in ["30 days","all-access trial","No credit card"]:
    assert token.lower() in pricing_text.lower(), token

print("ROOT2_FRONTIER_V2_BUILDKITE_INDEPENDENT_PASS__NAMED_CARRIER_WAKE_ONLY__SYNTHESIS_TWO_RESIDUALS__ZERO_CREDIT")


# Root2 V5 activation projection
V5_BASE=pathlib.Path("capsules/root2_v5_activation")
V5_EXPECTED={"root.json":"befa5e973c1861ec25e07fa45a74508c62bb68e6","bridge.json":"b0f97d4b02e2927a806ae12f16c4bb4e42fd83ae","terminal.json":"e47f25fb8e400fd34f83b0c0f74e6c8920170397","activation.json":"2d15df0daab51c5cc61c4194197da7f7fcd5a1b0"}
for _name,_sha in V5_EXPECTED.items():
    _p=V5_BASE/_name
    assert git_blob_sha(str(_p))==_sha, (_name,git_blob_sha(str(_p)),_sha)
_v5root=json.loads((V5_BASE/"root.json").read_text())
_v5bridge=json.loads((V5_BASE/"bridge.json").read_text())
_v5term=json.loads((V5_BASE/"terminal.json").read_text())
_v5act=json.loads((V5_BASE/"activation.json").read_text())
assert _v5act["subject"]["git_blob_sha"]=="e948022f0a4e8d91b949a5155d850d56aa137c87"
assert _v5act["verification"]["git_blob_sha"]=="2475a8583e2ed2889c3e9e0613ae3bcf269ffc82"
assert _v5act["authority"]["scheduling_authority"] is True
assert _v5act["authority"]["effective_scheduling_authority"] is True
assert _v5act["authority"]["execution_authority"] is False
assert _v5act["authority"]["promotion_authority"] is False
assert _v5act["authority"]["fresh_reality_authority"] is False
_ra=_v5root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert _ra["current_frontier_git_blob_sha"]=="e948022f0a4e8d91b949a5155d850d56aa137c87"
assert _ra["current_frontier_activation_git_blob_sha"]=="2d15df0daab51c5cc61c4194197da7f7fcd5a1b0"
assert _ra["effective_scheduling_authority"] is True
assert _v5root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
_ba=_v5bridge["root2_closure_controller_v2"]
assert _ba["frontier_git_blob_sha"]=="e948022f0a4e8d91b949a5155d850d56aa137c87"
assert _ba["frontier_activation_git_blob_sha"]=="2d15df0daab51c5cc61c4194197da7f7fcd5a1b0"
assert _ba["effective_scheduling_authority"] is True
_ta=_v5term["sources"]["root2_closure_v2_current_frontier"]
assert _ta["git_blob_sha"]=="e948022f0a4e8d91b949a5155d850d56aa137c87"
assert _ta["activation_git_blob_sha"]=="2d15df0daab51c5cc61c4194197da7f7fcd5a1b0"
assert _ta["effective_scheduling_authority"] is True
assert _v5root["current_acceptance"]["accepted_families"]==5
assert _v5root["current_acceptance"]["proved_atomic"]==12
assert _v5root["current_acceptance"]["unresolved_atomic"]==26
print("ROOT2_V5_ACTIVATION_PROJECTION_PASS__SCHEDULING_ONLY__ZERO_CREDIT")


# Root2 Frontier V6 finance compression projection
_V6_BASE=pathlib.Path("capsules/root2_v6_finance")
_V6_EXPECTED={
 "v5.json":"e948022f0a4e8d91b949a5155d850d56aa137c87",
 "v6.json":"fcbdb818b63b4986b026db29c400a47373a26fdb",
 "finance_threshold_activation.json":"9b9d4a41d19a5e58e8967027e1d1837790287dc2",
 "finance_mass.json":"ec36936e92a6111aed6b1813a45225fb4ca867dc",
 "finance_mass_verification.json":"cbdc6b3e773e86a1e57e119a6dd2c690ee1c6b11",
}
for _n,_sha in _V6_EXPECTED.items():
    assert git_blob_sha(str(_V6_BASE/_n))==_sha,(_n,git_blob_sha(str(_V6_BASE/_n)),_sha)

_v5=json.loads((_V6_BASE/"v5.json").read_text())
_v6=json.loads((_V6_BASE/"v6.json").read_text())
_thr=json.loads((_V6_BASE/"finance_threshold_activation.json").read_text())
_mass=json.loads((_V6_BASE/"finance_mass.json").read_text())
_massv=json.loads((_V6_BASE/"finance_mass_verification.json").read_text())

assert _v6["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"
assert _v6["source_bindings"]["prior_frontier_v5"]["git_blob_sha"]==_V6_EXPECTED["v5.json"]
assert _v6["source_bindings"]["finance_index_direct_threshold_activation"]["git_blob_sha"]==_V6_EXPECTED["finance_threshold_activation.json"]
assert _v6["source_bindings"]["finance_agent_v2_heldout_mass"]["git_blob_sha"]==_V6_EXPECTED["finance_mass.json"]
assert _v6["source_bindings"]["finance_agent_v2_heldout_mass"]["verification_git_blob_sha"]==_V6_EXPECTED["finance_mass_verification.json"]

for k in ["accepted_families","open_families","proved_atomic","unresolved_atomic","root1_positive_gap_count","root2_only_count","root3_only_count","root2_and_root3_count","root2_touching_predicates"]:
    assert _v6["exact_state"][k]==_v5["exact_state"][k],k
assert _v6["exact_state"]["accepted_families"]==5
assert _v6["exact_state"]["proved_atomic"]==12
assert _v6["exact_state"]["unresolved_atomic"]==26
assert _v6["exact_state"]["root2_touching_predicates"]==19

deltas={d["target"]+":"+d["deletion"] for d in _v6["projection_deltas"]}
assert "FINANCE_ACCOUNTING_INDEX_GE_61:COMPONENTWISE_OPUS_NONINFERIORITY_AS_MANDATORY_ROUTE" in deltas
assert "FINANCE_AGENT_V2_GE_58_59:OFFICIAL_HELDOUT_SUITE_SIZE_UNKNOWN" in deltas
assert _massv["independent_runner"]["conclusion"]=="success"
assert _mass["derived"]["heldout_questions_per_run"]==450
assert _mass["derived"]["runs_per_model"]==3
assert _mass["derived"]["scored_task_executions"]==1350
assert _thr["scheduling_effect"]["componentwise_opus_noninferiority"]=="SUFFICIENT_BUT_NOT_NECESSARY"

assert _v6["execution_authority"] is False
assert _v6["promotion_authority"] is False
assert _v6["fresh_reality_authority"] is False
assert _v6["accounting"]["acceptance_credit_delta"]==0
assert _v6["accounting"]["new_reality_units_consumed"]==0
assert _v6["accounting"]["terminal_cases_consumed"]==0

print("ROOT2_FRONTIER_V6_FINANCE_COMPRESSION_PROJECTION_PASS__ZERO_CREDIT__NO_FRESH_REALITY")
