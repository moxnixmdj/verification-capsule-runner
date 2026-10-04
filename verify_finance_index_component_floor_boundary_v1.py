import html
import json
import re
import urllib.request
from pathlib import Path

UA={"User-Agent":"project-brain-independent-verifier/1.0"}

def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=45) as r:
        assert 200 <= r.status < 300, (url,r.status)
        raw=r.read().decode("utf-8","replace")
    text=html.unescape(re.sub(r"<[^>]+>"," ",raw))
    return re.sub(r"\s+"," ",text).lower()

def any_phrase(text,*phrases):
    assert any(p.lower() in text for p in phrases), phrases

candidate=json.loads(Path("verification_inputs/finance_index_component_floor_boundary_v1.json").read_text())
direct=json.loads(Path("verification_inputs/finance_index_direct_threshold_theorem_v1.json").read_text())
agg=json.loads(Path("verification_inputs/finance_index_monotone_aggregation_receipt_v1.json").read_text())

assert candidate["schema"]=="PROJECT_BRAIN_FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY_20261004_V1"
assert candidate["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert candidate["parent_theorem"]["git_blob_sha"]=="37f47143f62fe2f59e56d8eca4a64bae18a1ce8b"
assert direct["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert direct["target"]=="61"
assert direct["compensation_across_components_allowed"] is True
assert "NO_DEFAULT_COMPONENT_FLOORS" in direct["rules"]
assert agg["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert agg["verified"]["all_weights_nonnegative"] is True
assert agg["verified"]["weight_sum"] == 1

floor_facts=candidate["underlying_evaluation_floor_facts"]
assert len(floor_facts)==8
assert all(x["proved_floor"]==0 for x in floor_facts)
assert {x["evaluation"] for x in floor_facts}=={
    "AA-Omniscience Business Accuracy",
    "GDPval-AA v2.1",
    "AA-Briefcase v1.1",
    "Humanity's Last Exam",
    "AutomationBench-AA Finance",
    "AA-LCR v1.1",
    "GDP.pdf",
    "AA-Omniscience Business Non-Hallucination",
}

intel=get(candidate["public_methodology"]["intelligence_benchmarking"])
omni=get(candidate["public_methodology"]["omniscience"])
automation=get(candidate["public_methodology"]["automationbench"])
hle=get(candidate["public_methodology"]["hle"])
lcr=get(candidate["public_methodology"]["lcr"])
gdp_pdf=get(candidate["public_methodology"]["gdp_pdf"])
briefcase=get(candidate["public_methodology"]["briefcase"])
cap=get(candidate["public_methodology"]["capability_index"])
finance=get("https://artificialanalysis.ai/models/capabilities/finance-and-accounting")

# First-party scoring semantics imply nonnegative raw/normalized evaluation scales.
any_phrase(intel,"clamp((elo - 500) / 2000)","clamp((elo-500)/2000)")
assert "aa-briefcase" in intel and "gdpval-aa" in intel
any_phrase(intel,"accuracy (10%) and 1 - hallucination rate (5%)","1 - hallucination rate")
any_phrase(intel,"objective completion, with zero credit for tasks that trigger a guardrail violation","objective completion")
assert "hle" in intel and "pass@1" in intel
assert "aa-lcr" in intel and "pass@1" in intel
any_phrase(intel,"all-pass headline and task-macro mean pass","all-pass")
any_phrase(omni,"proportion of correctly answered questions","accuracy")
any_phrase(automation,"share of task objectives","share of each task's objectives")
any_phrase(automation,"guardrail violation scores zero","guardrail violation")
any_phrase(hle,"percentage of answers the grader judges as correct","pass@1")
any_phrase(lcr,"average pass rate","pass/fail grading")
any_phrase(gdp_pdf,"all-pass","criterion pass rate")
any_phrase(briefcase,"elo and 95% confidence interval bounds are clamped at 0","clamped at 0")

# Bound public capability sources prove composition identity but not a usable hidden subscore floor.
assert "finance & accounting index" in cap
assert "business knowledge" in cap and "agentic knowledge work" in cap
assert "finance & accounting index" in finance
assert "weighted average of its capability sub-scores" in finance
assert "not publicly available" in finance

effect=candidate["scheduling_effect_if_verified"]
assert set(effect["delete"])=={
    "GENERIC_SEARCH_FOR_NEGATIVE_RANGES_OF_FINANCE_UNDERLYING_EVALUATIONS",
    "REPROVE_NONNEGATIVITY_OF_THE_EIGHT_LISTED_EVALUATION_SCALES",
}
assert effect["zero_floor_substitution_authorized"] is False
assert "CAPABILITY_SUBSCORE_AGGREGATION_OR_NORMALIZATION_TRANSFORM" in effect["preserve"]
assert "NO_FINANCE_CAPABILITY_SUBSCORE_ZERO_FLOOR_CLAIM" in candidate["hard_nonclaims"]
assert "NO_DEFAULT_ZERO_FLOORS" in candidate["hard_nonclaims"]
assert candidate["execution_authority"] is False
assert candidate["promotion_authority"] is False
assert candidate["fresh_reality_authority"] is False
assert candidate["accounting"]=={
    "incremental_spend_usd":0,
    "new_reality_units_consumed":0,
    "terminal_cases_consumed":0,
    "acceptance_credit_delta":0,
    "family_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0,
}

print("FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY: PASS")
