#!/usr/bin/env python3
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/root2_decision_only_activation_v1"
ACT=SUB/"ROOT2_DECISION_ONLY_EVALUATION_ACTIVATION_V1.json"
REC=SUB/"ROOT2_DECISION_ONLY_EVALUATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main():
    assert git_blob_sha(ACT)=="4086abe4559e30ade7bb7fa5be5571eaf40e94ee"
    assert git_blob_sha(REC)=="345ad6ce5d5ba5105c82e5663fa9a97e99ccec05"
    a=json.loads(ACT.read_text())
    r=json.loads(REC.read_text())
    assert r["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_DECISION_ONLY_COMPOSITION__ZERO_CREDIT"
    assert r["independent_runner"]["workflow_run_id"]==37190555353
    assert r["independent_runner"]["conclusion"]=="success"
    assert r["subjects"]["canonical/runtime/root2_decision_only_evaluation_v1.py"]=="bb70267e0bb44830a0c73708e3d4a07daecfdfa0"
    assert r["subjects"]["canonical/tests/test_root2_decision_only_evaluation_v1.py"]=="d2bfc3e49d1276a35e6351eda7ecb39945af71f3"
    assert r["subjects"]["canonical/governance/ROOT2_DECISION_ONLY_EVALUATION_V1.json"]=="e6a5409e9701bd1e62c39fce54ec4d4de4c22443"
    assert a["subject"]["runtime_git_blob_sha"]==r["subjects"]["canonical/runtime/root2_decision_only_evaluation_v1.py"]
    assert a["subject"]["tests_git_blob_sha"]==r["subjects"]["canonical/tests/test_root2_decision_only_evaluation_v1.py"]
    assert a["subject"]["governance_git_blob_sha"]==r["subjects"]["canonical/governance/ROOT2_DECISION_ONLY_EVALUATION_V1.json"]
    assert a["authority"]["scheduling"] is True
    assert a["authority"]["decision_certificate_compilation"] is True
    assert a["authority"]["execution"] is False
    assert a["authority"]["fresh_reality"] is False
    assert a["authority"]["promotion"] is False
    assert a["authority"]["acceptance_reduction"] is False
    p=a["preserved_truth"]
    assert (p["accepted_families"],p["proved_atomic"],p["unresolved_atomic"],p["root2_touching_predicates"])==(5,12,26,19)
    assert a["accounting"]["incremental_spend_usd"]==0
    assert a["accounting"]["new_reality_units_consumed"]==0
    assert a["accounting"]["acceptance_credit_delta"]==0
    assert "NO_RELATIVE_ELO_FROM_ABSOLUTE_BEHAVIOR_WITHOUT_VERIFIED_RELATIVE_SCORE_BRIDGE" in a["hard_rules"]
    assert "NO_MATCHED_NONINFERIORITY_COLLAPSE_TO_ONE_FIXED_BAR_BIT" in a["hard_rules"]
    print(json.dumps({"status":"PASS","activation_blob":git_blob_sha(ACT),"receipt_blob":git_blob_sha(REC),"zero_credit":True},sort_keys=True))
if __name__=="__main__": main()
