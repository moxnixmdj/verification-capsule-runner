import html
import json
import pathlib
import re
import subprocess
import urllib.request
from html.parser import HTMLParser

FILES={
  "audit":"subject/OPUS55_MATCHED_COMPARATOR_EFFORT_CONFIGURATION_AUDIT_V1.json",
  "super":"subject/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json",
  "protocols":"subject/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
  "registry":"subject/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
  "envelope":"subject/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
}
EXPECTED={
  "audit":"ad58a8d982868d6178b8725ef7520ab43b4078a3",
  "super":"d9ac894594ebcd2883520f7b7977a3548420541c",
  "protocols":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
  "registry":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
  "envelope":"661a57f839101fbf54c7e4edc76166c65ce9327d",
}
def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

audit=json.loads(pathlib.Path(FILES["audit"]).read_text())
sup=json.loads(pathlib.Path(FILES["super"]).read_text())
protocols=json.loads(pathlib.Path(FILES["protocols"]).read_text())
registry=json.loads(pathlib.Path(FILES["registry"]).read_text())
envelope=json.loads(pathlib.Path(FILES["envelope"]).read_text())

# No case exposure or acceptance mutation.
assert sup["case_generation"]["generated_now"] is False
assert sup["case_generation"]["exposed_now"] is False
assert sup["comparator_admissibility"]["current_state"]=="BLOCKED"
assert "NO_CASE_EXPOSURE_BEFORE_FREEZE" in sup["comparator_admissibility"]["required"]
assert audit["accounting"]=={
 "incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,
 "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0
}
assert audit["execution_authority"] is False
assert audit["promotion_authority"] is False
assert audit["fresh_reality_authority"] is False

# Generic matched configuration is frozen pre-exposure, without altering public fixed bars.
g=audit["configuration_classes"]["generic_matched_superportfolio"]
assert g["target_model"]=="Claude Opus 5.5"
assert g["thinking_mode"]=="adaptive"
assert g["effort"]=="max"
assert "BEFORE_FUTURE_POST_FREEZE_BEACON" in g["freeze_time"]
assert audit["route_admissibility_delta"]["conceptual_effort_choice_remaining"] is False
assert audit["route_admissibility_delta"]["provider_enforcement_remaining"] is True
native=audit["proof_protocol_interpretation"]["native_claude_api_generic_matched_request_freeze"]
assert native["model"]=="claude-opus-5-5"
assert native["thinking"].startswith("ADAPTIVE_ALWAYS_ON")
assert native["output_config"]=={"effort":"max"}
assert native["sampling"].startswith("DEFAULT_ONLY")

# TB4's xhigh provenance is explicitly local, not generalized.
tb=audit["configuration_classes"]["terminal_bench_4_fixed_bar"]
assert tb["predicate"]=="CODING_TB4_GE_66_4"
assert tb["frozen_score"]==66.4
assert tb["published_opus_configuration"]=="XHIGH_EFFORT"
assert "DOES_NOT_FORCE_ALL_GENERIC_MATCHED_SUPERPORTFOLIO_RUNS_TO_XHIGH" in tb["consequence"]

# Frozen scalar bars remain byte-identical registry facts. Effort metadata is not a new Brain pass condition.
bars={p["id"]:p["acceptance"] for p in registry["predicates"] if p["kind"]=="PUBLIC_FIXED_BAR"}
expected_bars={
 "CODING_TB4_GE_66_4":"Terminal-Bench 4.0 >= 66.4%",
 "CODING_FRONTIERCODE_GE_54_4":"FrontierCode v1.1 Main >= 54.4%",
 "CODING_CURSORBENCH_GE_57_8":"CursorBench 4.0 >= 57.8%",
 "PROWORK_GDPVAL_GE_1846":"GDPval-AA v2.1 >= 1846 Elo",
 "PROWORK_AA_BRIEFCASE_GE_1822":"AA-Briefcase v1.1 >= 1822 Elo",
 "AUTOMATIONBENCH_GE_40":"AutomationBench >= 40.0%",
 "HLE_TOOLS_GE_67_7":"Humanity's Last Exam with tools >= 67.7%",
 "TB_SCIENCE_GE_58_7":"Terminal-Bench-Science 0.1 >= 58.7%",
 "CHARTOGRAPHY_TOOLS_GE_89":"Chartography with tools >= 89.0%",
}
for k,v in expected_bars.items():
    assert bars[k]==v,(k,bars.get(k),v)

# Third-party fixed bars must not inherit Anthropic's general effort statement.
third=audit["configuration_classes"]["third_party_fixed_bars"]
for p in ("FINANCE_ACCOUNTING_INDEX_GE_61","FINANCE_AGENT_V2_GE_58_59","LIVEBENCH_IF_GE_65_7","MYSTERYMECHANISM_GE_49_55"):
    assert p in third["examples"]
assert "DO_NOT_INHERIT_ANTHROPIC_GLOBAL_EFFORT_METADATA" in third["rule"]

# Canonical protocol requires same frozen scope/harness and fail-closed comparability.
assert "same frozen task population/harness/tool authority" in protocols["universal_rules"]["same_scope"]
assert "incomparable harness" in protocols["universal_rules"]["unknown"]
assert envelope["acceptance_rule"]=="BRAIN_CONFIGURED_CAPABILITY_MUST_EQUAL_OR_EXCEED_OPUS_5_5_ON_RELEVANT_USEFUL_CONDITIONS"

class T(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self,d):
        if d.strip(): self.parts.append(d)
def fetch_text(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read().decode("utf-8","replace")
    p=T(); p.feed(raw)
    return re.sub(r"\\s+"," ",html.unescape(" ".join(p.parts)))

text=fetch_text("https://www.anthropic.com/claude-opus-5-5")
assert "Unless otherwise noted, all Claude Opus 5.5 results use adaptive thinking at max effort." in text
assert "Terminal-Bench 4.0 results are reported for Claude Opus 5.5 at xhigh effort" in text
assert "At max effort, Opus 5.5 scores 1846 Elo" in text
assert "At default effort (medium), Opus 5.5 scores 54.6%" in text
assert "At default effort (medium), Opus 5.5 scores 52.5%" in text

effort=fetch_text("https://platform.claude.com/docs/en/build-with-claude/effort")
assert "Set output_config.effort on the request." in effort
assert "You can raise the effort level to max for the absolute highest capability" in effort
assert "Claude Opus 5.5 supports all five effort levels" in effort
assert "medium is the default" in effort

migration=fetch_text("https://platform.claude.com/docs/en/models/opus-5-5/migration-guide")
assert "claude-opus-5-5" in migration
assert "Adaptive thinking is always on" in migration
assert "All five levels" in migration
assert "temperature" in migration and "top_p" in migration and "top_k" in migration

# Critical anti-weakening / anti-overclaim assertions.
nonclaims="\n".join(audit["hard_nonclaims"])
assert "NO_CLAIM_XHIGH_EQUALS_MAX" in nonclaims
assert "NO_CLAIM_XHIGH_IS_THE_GENERIC_MATCHED_COMPARATOR_CONFIGURATION" in nonclaims
assert "NO_CLAIM_THIRD_PARTY_OWNER_BENCHMARKS_USED_ANTHROPIC_MAX_EFFORT_UNLESS_OWNER_OR_PRIMARY_SOURCE_PROVES_IT" in nonclaims
assert "NO_MATCHED_CASE_GENERATION_OR_EXPOSURE" in nonclaims
assert "NO_CLAIM_PROVIDER_MODEL_NAME_ALONE_PROVES_EFFORT_THINKING_SAMPLING_OR_TOOL_SEMANTIC_EQUIVALENCE" in nonclaims

print("PASS: Anthropic current source binds general Opus 5.5 benchmark default to adaptive thinking max effort")
print("PASS: TB4 xhigh exception remains local to frozen 66.4 bar")
print("PASS: fixed public bars remain scalar comparator facts; no new Opus run required")
print("PASS: generic live matched comparator effort is frozen pre-exposure to adaptive max")
print("PASS: native Opus55 matched request contract frozen to exact model + adaptive/max + default sampling")\nprint("PASS: provider enforcement/identity/cost/harness remain open; zero cases/spend/credit")
