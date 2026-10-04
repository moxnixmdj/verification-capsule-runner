#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"brain"
RECEIPT=ROOT/"receipt.json"

EXPECTED={
"canonical/runtime/prepromotion_falsification_gate_v1.py":"53b9dfd76551682e03720b23e0f331533a75ae4c",
"canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V5.json":"3f42ef48382cf2d298fe1c9f97387915c3139c4b",
"canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V5_LIVEBENCH_UNION25_OVERLAY.json":"c0450c277fa8b2476da736cae910360aee4e45a4",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"dd85ca4bb01193220a24afbb189365937024b2a8",
"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":"919da676976043e5b501f207d3cf420dc4fb50b1",
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"290a02dd1ce3b1174b9bf678356ea3012541c148",
"canonical/governance/LIVEBENCH_SCOPE_UNION_BREAKTHROUGH_20261005_V1.json":"db40a9252f65af4782bec23710f3ec5acbff617f",
"canonical/verification/LIVEBENCH_PUBLIC_SCOPE_UNION_INDEPENDENT_VERIFICATION_20261005_V1.json":"18c78a49e39aca26bd50f94cda64ba189167bd80",
"canonical/verification/LIVEBENCH_FULL_CROSS_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json":"c9f2c5d8f764cb61e8b5737de1155f14bc3f73d1",
}

def blob_sha(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel):
    return json.loads((SUB/rel).read_text(encoding="utf-8"))

checks=[]
def ck(x,m):
    if not x: raise AssertionError(m)

try:
    for rel,sha in EXPECTED.items():
        ck(blob_sha(SUB/rel)==sha,"BLOB_MISMATCH:"+rel)
    checks.append("EXACT_SUBJECT_BLOBS")

    gp=SUB/"canonical/runtime/prepromotion_falsification_gate_v1.py"
    spec=importlib.util.spec_from_file_location("gate",gp)
    gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    H="a"*40
    def R(ind=False):
        return {"status":"PASS","content_addressed":True,"receipt_sha":H,"independent":ind}
    def base():
        return {"candidate_id":"independent-test","claim_type":"UNIVERSAL_FORMAL",
        "risk_features":{k:False for k in gate.RISK_REQUIREMENTS},
        "receipts":{"SUBJECT_BYTES_BOUND":R(),"QUANTIFIED_DOMAIN_BOUND":R(),
        "COUNTEREXAMPLE_SEARCH_PASS":R(),"BOUNDARY_SEARCH_PASS":R(),
        "METAMORPHIC_SEARCH_PASS":R(),"INDEPENDENT_REPLAY_PASS":R(True),
        "SEPARATE_REDUCTION_PRECOMMIT":R()},
        "known_counterexamples":[],"post_outcome_rule_change":False}
    o=gate.evaluate(base())
    ck(o["eligible_for_separate_reduction"] is True,"COMPLETE_GATE_REJECTED")
    ck(not o["acceptance_credit"] and not o["promotion_authority"],"GATE_GRANTED_CREDIT")
    for flag,ob in gate.RISK_REQUIREMENTS.items():
        x=base(); x["risk_features"][flag]=True
        q=gate.evaluate(x)
        ck(q["status"]=="FAIL_CLOSED" and any(ob in e for e in q["errors"]),"RISK_NOT_GATED:"+flag)
        x["receipts"][ob]=R()
        ck(gate.evaluate(x)["eligible_for_separate_reduction"] is True,"RISK_RECEIPT_NOT_ACCEPTED:"+flag)
    x=base(); x["known_counterexamples"]=["reachable"]
    ck("KNOWN_COUNTEREXAMPLE_REMAINS_OPEN" in gate.evaluate(x)["errors"],"OPEN_COUNTEREXAMPLE_NOT_BLOCKED")
    x=base(); x["receipts"]["INDEPENDENT_REPLAY_PASS"]=R(False)
    ck("INDEPENDENT_REPLAY_NOT_INDEPENDENT" in gate.evaluate(x)["errors"],"FAKE_INDEPENDENCE_NOT_BLOCKED")
    x=base(); x["post_outcome_rule_change"]=True
    ck("POST_OUTCOME_RULE_CHANGE_FORBIDDEN" in gate.evaluate(x)["errors"],"POST_OUTCOME_CHANGE_NOT_BLOCKED")
    checks.append("ADVERSARIAL_GATE")

    reg=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
    led=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    roots=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
    auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    pol=load("canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V5.json")
    overlay=load("canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V5_LIVEBENCH_UNION25_OVERLAY.json")
    ids={r.get("predicate_id") or r.get("id") for r in reg["predicates"]}
    proved={r["predicate_id"] for r in led["claims"] if r.get("state")=="PROVED"}
    unresolved=ids-proved
    ck(len(ids)==38 and len(proved)==13 and len(unresolved)==25,"LEDGER_COUNTS")
    ck(set(pol["residual_predicates"])==unresolved,"POLICY_NOT_LEDGER_COMPLEMENT")
    fronts=[set(pol["macro_actions"][i]["target_predicates"]) for i in range(3)]
    ck(not(fronts[0]&fronts[1] or fronts[0]&fronts[2] or fronts[1]&fronts[2]),"FRONTS_OVERLAP")
    ck(set().union(*fronts)==unresolved,"FRONTS_NOT_COMPLETE")
    ck("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in unresolved,"CLOSED_UNKNOWN_REOPENED")
    ck(pol["macro_actions"][3]["target_predicates"]=="SURVIVING_RESIDUAL_ONLY","EMPIRICAL_NOT_RESIDUAL_ONLY")
    ck(not pol["execution_authority"] and not pol["promotion_authority"] and not pol["fresh_reality_authority"],"POLICY_AUTHORITY_LEAK")
    rp=roots["current_residual_root_partition"]; ap=auth["current_root_partition_override"]
    ck((rp["unresolved_total"],rp["root1_positive_gap_count"],rp["root2_only_count"],rp["root3_only_count"],rp["root2_and_root3_count"])==(25,0,16,6,3),"ROOT_DRIFT")
    ck((ap["proved_atomic"],ap["unresolved_atomic"],ap["root1_positive_gap_count"],ap["root2_only"],ap["root3_only"],ap["root2_and_root3"])==(13,25,0,16,6,3),"AUTH_DRIFT")
    ck(pol["acceptance_binding"]["git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"],"POLICY_LEDGER_BIND")
    ck(pol["root_binding"]["git_blob_sha"]==EXPECTED["canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"],"POLICY_ROOT_BIND")
    ck(pol["terminal_authority_binding"]["git_blob_sha"]==EXPECTED["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"],"POLICY_AUTH_BIND")
    checks.append("POLICY_25_WAY_PARTITION")

    scope=load("canonical/governance/LIVEBENCH_SCOPE_UNION_BREAKTHROUGH_20261005_V1.json")
    scopev=load("canonical/verification/LIVEBENCH_PUBLIC_SCOPE_UNION_INDEPENDENT_VERIFICATION_20261005_V1.json")
    cross=load("canonical/verification/LIVEBENCH_FULL_CROSS_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json")
    ck(scope["scope_lattice"]["public_union_count"]==25,"UNION_COUNT")
    ck(scope["scope_lattice"]["public_union_equals_entire_pinned_registry"] is True,"UNION_NOT_REGISTRY")
    ck(scope["verified_structural_quotient"]["compatible_structural_set_total_1_to_5"]==14559,"UNION_STRUCTURAL_COUNT")
    ck("PASS" in scopev["status"],"UNION_INDEPENDENT_NOT_PASS")
    ck(cross["exact_result"]["total_cases"]==712704 and cross["exact_result"]["exact_pointwise_matches"]==712704,"ACTIVE15_CROSS_DRIFT")
    ck(cross["accounting"]["acceptance_credit_delta"]==0,"ACTIVE15_PREMATURE_CREDIT")
    ck(overlay["verified_delta"]["full_registry_family_count"]==25,"OVERLAY_COUNT")
    ck(overlay["verified_delta"]["compatible_structural_sets_1_to_5"]==14559,"OVERLAY_STRUCTURAL")
    ck(overlay["scheduler_override"]["supersede_base_livebench_strategy"] is True,"OVERLAY_NOT_SUPERSEDING")
    ck("FULL_PINNED_REGISTRY25" in overlay["scheduler_override"]["strategy"],"OVERLAY_WRONG_TARGET")
    ck(overlay["accounting"]["acceptance_credit_delta"]==0 and not overlay["promotion_authority"],"OVERLAY_CREDIT_LEAK")
    checks.append("UNION25_OVERLAY_BINDING")

    result={"schema":"PROJECT_BRAIN_POLICY_V5_INDEPENDENT_FASTLANE_VERIFICATION_20261005_V1",
    "status":"INDEPENDENT_PASS","pass":True,"checks":checks,
    "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
    "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    "fresh_reality_authority":False}
    RECEIPT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
except Exception as e:
    result={"schema":"PROJECT_BRAIN_POLICY_V5_INDEPENDENT_FASTLANE_VERIFICATION_20261005_V1",
    "status":"INDEPENDENT_FAIL","pass":False,"checks":checks,
    "error":type(e).__name__+":"+str(e),"acceptance_credit_delta":0}
    RECEIPT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    raise
