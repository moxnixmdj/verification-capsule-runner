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


# Root2 OSWorld methodology + Finance Agent v2 zero-cost boundary
_os_path=pathlib.Path("subject/OSWORLD_OPUS55_METHODOLOGY_PUBLIC_CORROBORATION_20261004_V1.json")
_fin_path=pathlib.Path("subject/FINANCE_AGENT_V2_ZERO_COST_TOOL_BOUNDARY_20261004_V1.json")
assert git_blob_sha(str(_os_path))=="259a6fa8f7daf744e6e06902d43925419cdd4d9b"
assert git_blob_sha(str(_fin_path))=="032caa374280983945321f0a5706c0c665c097a6"
_os=json.loads(_os_path.read_text())
_fin=json.loads(_fin_path.read_text())
assert "EXACT_SEPTEMBER_10_ANTHROPIC_COMPONENT_SNAPSHOT_EQUALS_UPSTREAM_OSWORLD_V2_1_PINNED_COMPONENT_HASHES" in _os["still_open"]
assert _os["fresh_reality_authority"] is False
assert _fin["first_party_runner"]["public_question_file"]["public_question_count"]==27
assert _fin["first_party_runner"]["agent_runtime"]["default_max_turns"] is None
assert "OFFICIAL_HELDOUT_SUITE_SIZE_OR_EQUIVALENT_EXECUTION_BOUND" in _fin["preserve"]
assert _fin["fresh_reality_authority"] is False

_anth=fetch("https://www.anthropic.com/claude-opus-5-5")
_anth_text=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",_anth))
for token in ["OSWorld 2.1","81.8"]:
    assert token.lower() in _anth_text.lower(), token

_card=fetch("https://malob.github.io/ai-system-cards/anthropic/claude-opus-5-5/")
_card_text=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",_card))
for token in ["108 long-horizon computer use tasks","1080p resolution","500 action steps","Claude Opus 4.8","September 10, 2026","81.8%","48.7%"]:
    assert token.lower() in _card_text.lower(), token

_release=json.loads(fetch("https://api.github.com/repos/xlang-ai/OSWorld-V2/releases/tags/osworld-v2.1"))
assert _release["tag_name"]=="osworld-v2.1"
assert "All 108 task files" in _release["body"]
assert "Task-Web/OSWorld-web@osworld-v2.1" in _release["body"]

_public=fetch("https://raw.githubusercontent.com/vals-ai/finance-agent-v2/main/data/public.txt")
assert len([x for x in _public.splitlines() if x.strip()])==27
_agent=fetch("https://raw.githubusercontent.com/vals-ai/finance-agent-v2/main/finance_agent/get_agent.py")
assert "MAX_TIME_SECONDS = 2 * 60 * 60" in _agent
assert "max_turns: int | None = None" in _agent

_tav=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",fetch("https://www.tavily.com/pricing")))
for token in ["1,000 API credits","No credit card required","requests will stop"]:
    assert token.lower() in _tav.lower(), token
_sec=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",fetch("https://sec-api.io/pricing")))
for token in ["Free Tier","first 100 API calls"]:
    assert token.lower() in _sec.lower(), token
_tiingo=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",fetch("https://www.tiingo.com/pricing")))
for token in ["$0/month","Max Requests Per Hour","50","Max Requests Per Day","1000"]:
    assert token.lower() in _tiingo.lower(), token

print("ROOT2_OSWORLD_FINANCE_ZERO_REALITY_REDUCTION_PUBLIC_RUNNER_PASS__ZERO_CREDIT")
