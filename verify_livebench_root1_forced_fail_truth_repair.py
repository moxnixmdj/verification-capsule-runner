#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

BASE=Path("capsules/livebench_root1_truth_repair/brain")
EXPECTED={
 "CANDIDATE.json":"07f05c307e4869051be42797fb6898e918a800bd",
 "ROOT_STATE.json":"c3d1e25e2268cce90df545a93f107aa24fed8f8b",
 "TRUTH_REPAIR.json":"359f740191e528f16b30ed6b893dad5caee5698d",
 "LOCAL_RECLASS.json":"eef18a73b23db53082b934976bcbd05cab9c5684",
 "ROOT_PROJECTION.json":"21dc5e07e18ba3e99a97ffef20a098833c684e99",
 "FORCED_FAIL.json":"98659983c43ac37508177b4003a08cfd5d1e9447",
}
def blob_sha(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(name):
    b=(BASE/name).read_bytes()
    assert blob_sha(b)==EXPECTED[name],(name,blob_sha(b),EXPECTED[name])
    return json.loads(b)
def flat_strings(x):
    if isinstance(x,dict):
        for k,v in x.items():
            yield str(k)
            yield from flat_strings(v)
    elif isinstance(x,list):
        for v in x: yield from flat_strings(v)
    else:
        yield str(x)

def main():
    cand=load("CANDIDATE.json")
    root=load("ROOT_STATE.json")
    truth=load("TRUTH_REPAIR.json")
    reclass=load("LOCAL_RECLASS.json")
    proj=load("ROOT_PROJECTION.json")
    forced=load("FORCED_FAIL.json")

    assert cand["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
    assert truth["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
    assert truth["status"].startswith("ACTIVE_TRUTH_REPAIR__UNSOUND_FORCED_FAIL_INFERENCE_REMOVED")
    assert truth["bug"]["logical_error"]=="LOWER_BOUND_EVIDENCE_DOES_NOT_IMPLY_EXACTNESS_OR_AN_UPPER_BOUND"
    assert truth["repair"]["default_case_score_upper_bound"]==1.0

    blockers=root["roots"]["root_1_capability_missing"]["current_positive_root1_blockers"]
    assert len(blockers)==1
    assert blockers[0]["predicate_id"]=="LIVEBENCH_IF_GE_65_7"
    assert "FORCED_FAIL" in blockers[0]["state"]
    assert blockers[0]["forced_fail_binding"]=="canonical/governance/LIVEBENCH_V6_FORCED_FAIL_BINDING_V1.json"

    reclass_text="\n".join(flat_strings(reclass))
    proj_text="\n".join(flat_strings(proj))
    assert "LIVEBENCH_IF_GE_65_7" in reclass_text and "FORCED_FAIL" in reclass_text
    assert "LIVEBENCH_IF_GE_65_7" in proj_text and "ROOT1" in proj_text

    tp=forced["threshold_proof"]
    assert tp["population_count"]==200
    assert abs(float(tp["threshold_percent"])-65.7)<1e-12
    assert tp["observed_zero_count"]==72
    assert tp["unobserved_remaining_count"]==128
    assert float(tp["conservative_full_population_upper_percent"])==64.0

    # Independent logic check. A lower bound of 0 for 72 cases does not cap them at 0.
    threshold_mass=200*65.7/100
    old_assumed_upper_mass=128
    sound_upper_mass=72*1.0+128*1.0
    assert old_assumed_upper_mass < threshold_mass
    assert sound_upper_mass == 200.0
    assert not (sound_upper_mass < threshold_mass)

    repaired=cand["repaired_partition_candidate"]
    assert repaired=={
      "unresolved_total":26,
      "root1_positive_gap_count":0,
      "root1_only_count":0,
      "root2_only_count":16,
      "root3_only_count":7,
      "root2_and_root3_count":3,
      "livebench_location":"ROOT2_ONLY",
      "acceptance_counts_unchanged":True,
      "accepted_families":5,
      "proved_atomic":12,
      "unresolved_atomic":26,
    }
    assert repaired["root2_only_count"]+repaired["root3_only_count"]+repaired["root2_and_root3_count"]==26

    assert cand["logical_repair"]["reclassification"]["after"].startswith("ROOT2_ONLY")
    assert cand["authority"]=={
      "scheduling":False,"execution":False,"promotion":False,
      "fresh_reality":False,"acceptance_credit":False
    }
    assert all(cand["accounting"][k]==0 for k in [
      "incremental_spend_usd","terminal_cases_consumed","acceptance_credit_delta",
      "family_credit_delta","capability_credit_delta","ownership_credit_delta"
    ])

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_ROOT1_FORCED_FAIL_TRUTH_REPAIR_PUBLIC_RUNNER_VERIFICATION_V1",
      "status":"PASS",
      "verified_candidate_git_blob_sha":EXPECTED["CANDIDATE.json"],
      "verified_source_git_blob_shas":EXPECTED,
      "verified":{
        "prior_root1_depends_on_livebench_forced_fail":True,
        "prior_forced_fail_used_72_lower_bound_zero_cases_as_if_upper_zero":True,
        "lower_bound_zero_does_not_imply_upper_bound_zero":True,
        "sound_conservative_upper_mass":sound_upper_mass,
        "threshold_mass":threshold_mass,
        "forced_fail_not_proved_by_bound":True,
        "root1_positive_gap_premise_revoked":True,
        "livebench_reverts_to_root2_only_under_current_classification_rule":True,
        "repaired_partition":"0_ROOT1__16_ROOT2_ONLY__7_ROOT3_ONLY__3_MIXED",
      },
      "accounting":{"terminal_cases_consumed":0,"acceptance_credit_delta":0}
    }
    Path("livebench_root1_forced_fail_truth_repair_verification_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
