#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SUB = Path("subject/mystery_root_v2_20261005")
OUT = Path("mystery_root_v2_verification.json")
CANDIDATE_NAME = "canonical__governance__MYSTERYMECHANISM_ROOT_CLASSIFICATION_TRUTH_REPAIR_V2.json"
EXPECTED_CANDIDATE_BLOB = "2b426aba860906446326ad01b0a4acf0c74de5b4"
TARGET = "MYSTERYMECHANISM_GE_49_55"
BEHAVIORS = {
    "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
    "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
}

def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def read_name(name: str):
    p = SUB / name
    raw = p.read_bytes()
    return json.loads(raw), blob_sha(raw)

def snap_name(path: str) -> str:
    return path.replace("/", "__")

def fail(msg: str):
    raise AssertionError(msg)

candidate, candidate_sha = read_name(CANDIDATE_NAME)
if candidate_sha != EXPECTED_CANDIDATE_BLOB:
    fail(f"CANDIDATE_BLOB_DRIFT:{candidate_sha}")

# Every authority input is independently re-hashed from copied immutable bytes.
loaded = {}
for key, ref in candidate["exact_inputs"].items():
    doc, got = read_name(snap_name(ref["path"]))
    if got != ref["git_blob_sha"]:
        fail(f"BOUND_BLOB_MISMATCH:{key}:{got}:{ref['git_blob_sha']}")
    loaded[key] = doc

registry = loaded["predicate_registry"]
pred = next((x for x in registry["predicates"] if x.get("predicate_id") == TARGET), None)
if pred is None:
    fail("TARGET_PREDICATE_MISSING")
if pred.get("kind") != "PUBLIC_FIXED_BAR":
    fail("TARGET_KIND_DRIFT")
if "49.55" not in str(pred.get("acceptance")):
    fail("TARGET_THRESHOLD_DRIFT")

ledger = loaded["acceptance_ledger"]
claim = next((x for x in ledger["claims"] if x.get("predicate_id") == TARGET), None)
if claim is None or claim.get("state") == "PROVED":
    fail("TARGET_MUST_REMAIN_UNPROVED_BEFORE_RECLASSIFICATION")

root = loaded["root_state"]
part = root["current_residual_root_partition"]
if TARGET not in part["root2_only"]:
    fail("CURRENT_ROOT2_MEMBERSHIP_REQUIRED")
if (part["unresolved_total"], part["root2_only_count"], part["root3_only_count"], part["root2_and_root3_count"]) != (25,16,6,3):
    fail("CURRENT_ROOT_COUNTS_DRIFT")

recon = loaded["private_route_deletion_reconciliation"]
if recon["distinction"]["benchmark_substitution"]["current_admitted_count"] != 0:
    fail("PROXY_SUBSTITUTION_MUST_REMAIN_ZERO")
if recon["distinction"]["benchmark_substitution"]["authority"] is not False:
    fail("PROXY_SUBSTITUTION_AUTHORITY_MUST_REMAIN_FALSE")
route = next((x for x in recon["current_route_deletions"] if x.get("surface") == "Vals MysteryMechanism"), None)
if route is None:
    fail("MYSTERY_ROUTE_DELETION_MISSING")
if set(route["represented_contracts"]) != BEHAVIORS:
    fail("REPRESENTED_BEHAVIOR_SET_DRIFT")
if "T3_MUST_DIRECTLY_INSTRUMENT_AND_PASS_ALL_REPRESENTED_CONTRACTS" not in route["terminal_requirement_remaining"]:
    fail("DIRECT_TERMINAL_REQUIREMENT_MISSING")
required_anti = {
    "BENCHMARK_ROUTE_DELETION_IS_NOT_FAMILY_PROOF",
    "BENCHMARK_ROUTE_DELETION_IS_NOT_A_CLAIM_OF_MATCHING_THE_PRIVATE_BENCHMARK_SCORE",
    "ALL_REPRESENTED_BEHAVIORAL_CONTRACTS_REMAIN_IN_THE_TERMINAL_PORTFOLIO_AND_MUST_PASS_THEIR_FROZEN_ACCEPTANCE",
}
if not required_anti.issubset(set(recon["anti_weakening"])):
    fail("ANTI_WEAKENING_GUARD_MISSING")

dominance = loaded["private_route_dominance"]
if dominance["blocked_route_verdicts"]["BLOCKED_MYSTERYMECHANISM"]["redundant"] is not True:
    fail("PRIVATE_ROUTE_NOT_VERIFIED_REDUNDANT")
if dominance.get("target_weakening") is not False:
    fail("DOMINANCE_TARGET_WEAKENING")

domverify = loaded["private_route_dominance_verification"]
if "BLOCKED_MYSTERYMECHANISM_REDUNDANT" not in domverify["conclusions"]:
    fail("INDEPENDENT_DOMINANCE_CONCLUSION_MISSING")
if "ROUTE_DELETION_DOES_NOT_INHERIT_PRIVATE_SCORE_OR_GRANT_FAMILY_CREDIT" not in domverify["conclusions"]:
    fail("INDEPENDENT_NO_SCORE_INHERITANCE_MISSING")

spec = loaded["independent_acceptance_model_evidence"]
if "WHOLE_SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001" not in spec["not_owned"]:
    fail("SPEC_WHOLE_SCOPE_GAP_NOT_PRESERVED")

research = loaded["research_control_verification"]
limits = set(research["limitations"])
if "PREWAVE_BINDING_ONLY" not in limits or "NOT_CURRENT_BYTE_PROMOTION_AUTHORITY" not in limits:
    fail("RESEARCH_CONTROL_SCOPE_GAP_NOT_PRESERVED")

ud = loaded["unknown_domain_v6_reduction"]
if ud.get("target_predicate") != "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT":
    fail("UNKNOWN_DOMAIN_V6_TARGET_DRIFT")
if ud["deduction"]["new_state"] != "PROVED" or ud["deduction"]["scope_complete"] is not True:
    fail("UNKNOWN_DOMAIN_V6_NOT_PROVED")
if "MYSTERYMECHANISM_GE_49_55" not in ud["deduction"]["reason_family_remains_open"]:
    fail("UNKNOWN_DOMAIN_FAMILY_SEPARATION_NOT_PRESERVED")

repair = candidate["root_reclassification"]
if (repair["before"], repair["after"]) != ("ROOT2_ONLY","ROOT3_ONLY"):
    fail("RECLASSIFICATION_DIRECTION_INVALID")
if (repair["unresolved_total_before"], repair["unresolved_total_after"]) != (25,25):
    fail("RECLASSIFICATION_MUST_NOT_CHANGE_ACCEPTANCE")
if (repair["root2_only_count_before"], repair["root2_only_count_after"]) != (16,15):
    fail("ROOT2_COUNT_DELTA_INVALID")
if (repair["root3_only_count_before"], repair["root3_only_count_after"]) != (6,7):
    fail("ROOT3_COUNT_DELTA_INVALID")
if (repair["root2_touching_before"], repair["root2_touching_after"]) != (19,18):
    fail("ROOT2_TOUCHING_DELTA_INVALID")
if (repair["root3_touching_before"], repair["root3_touching_after"]) != (9,10):
    fail("ROOT3_TOUCHING_DELTA_INVALID")

gaps = candidate["live_closure_obligation"]["known_load_bearing_gaps"]
if "WHOLE_BEHAVIOR_EXPLICITLY_NOT_OWNED" not in gaps["specification_to_independent_acceptance_model_001"]:
    fail("SPEC_GAP_NOT_FAIL_CLOSED")
if candidate["live_closure_obligation"]["current_state"] != "OPEN":
    fail("LIVE_CLOSURE_MUST_REMAIN_OPEN")
if candidate["scheduling_effect"]["promotion_authority"] is not False:
    fail("RECLASSIFICATION_MUST_HAVE_ZERO_PROMOTION_AUTHORITY")

acct = candidate["accounting"]
for key in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta","proved_predicate_delta","unresolved_predicate_delta","incremental_spend_usd","new_reality_units_consumed"):
    if acct[key] != 0:
        fail(f"NONZERO_ACCOUNTING:{key}")

result = {
    "schema":"PROJECT_BRAIN_MYSTERYMECHANISM_ROOT_CLASSIFICATION_TRUTH_REPAIR_V2_INDEPENDENT_VERIFICATION",
    "status":"PASS__TARGET_PRESERVING_ROOT2_TO_ROOT3_RECLASSIFICATION__SCOPE_COMPLETENESS_REMAINS_OPEN__ZERO_ACCEPTANCE_CREDIT",
    "candidate_blob_sha":candidate_sha,
    "verified":{
        "private_score_route_deleted_as_required_execution_route":True,
        "proxy_benchmark_substitution_authority":False,
        "private_score_equivalence_claimed":False,
        "represented_behavior_set_exact":sorted(BEHAVIORS),
        "whole_specification_acceptance_behavior_gap_preserved":True,
        "research_control_prewave_gap_preserved":True,
        "unknown_domain_v6_transfer_audit_proved":True,
        "root2_to_root3_count_delta_exact":True,
        "atomic_predicate_remains_unproved":True,
        "promotion_authority":False,
    },
    "accounting":{
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
        "new_reality_units_consumed":0,
    }
}
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(result,sort_keys=True))
