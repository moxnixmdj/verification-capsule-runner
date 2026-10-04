from __future__ import annotations
import hashlib, importlib, json
from pathlib import Path

from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import (
    TRANSFER, ABSTAIN, UnknownDomainScorerError, score_case, aggregate
)

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"fb180c4a13158cc8382435dd6fb51c187ebb9321",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/tests/test_unknown_domain_direct_hidden_scorer_v1.py":"fbea87d7d05647af2dfb66ef344908dfd055e5c0",
}

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def exact_bytes():
    for p,sha in EXPECTED.items():
        got=git_blob((ROOT/p).read_bytes())
        assert got==sha,(p,got,sha)

def family_freeze():
    d=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json").read_text())
    assert d["accounting"]["generated_case_count"]==0
    assert d["accounting"]["terminal_cases_consumed"]==0
    assert d["scoring"]["aggregation"].startswith("ALL_CASES")
    counts={x["leaf_id"]:x["case_count"] for x in d["leaves"]}
    assert counts[TRANSFER]==12 and counts[ABSTAIN]==15
    balance=next(x for x in d["leaves"] if x["leaf_id"]==ABSTAIN)["class_balance"]
    assert balance=={"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5}
    assert "NO_ACTUAL_CASES_EXIST_IN_THIS_FREEZE" in d["hard_rules"]
    assert "NO_CANDIDATE_BYTES_BOUND_IN_THIS_FREEZE" in d["hard_rules"]

def run_copied_tests():
    mod=importlib.import_module("canonical.tests.test_unknown_domain_direct_hidden_scorer_v1")
    names=sorted(n for n in dir(mod) if n.startswith("test_") and callable(getattr(mod,n)))
    assert names
    for name in names:
        getattr(mod,name)()
    return names

def good_transfer():
    h={
      "leaf_id":TRANSFER,"case_id":"T","gold_terminal_consequence":"GO",
      "domain_a_earned_receipt_ids":["R1"],"full_rediscovery_probe_floor":3,
      "latent_primitive_fingerprint":"prim:x",
      "domain_a_receipt_primitive_bindings":{"R1":"prim:x"},
      "surface_label_permutation_verified":True,"domain_vocabularies_disjoint":True,
      "transfer_relevant_feature_ids":["F1"],"distractor_feature_ids":["D1","D2"],
    }
    t={
      "decision":"CONCLUDE","terminal_consequence":"GO",
      "domain_a_source_receipt_ids":["R1"],"transferred_primitive_fingerprint":"prim:x",
      "domain_b_discovery_probe_count":1,"support_feature_ids":["F1"],
      "negative_transfer_rejected_feature_ids":["D1","D2"],"mapping_basis":"CAUSAL_ISOMORPHISM",
      "evidence_provenance":[
       {"evidence_id":"R1","source":"A","receipt":"x"},
       {"evidence_id":"F1","source":"B","receipt":"x"},
       {"evidence_id":"D1","source":"B","receipt":"x"},
       {"evidence_id":"D2","source":"B","receipt":"x"},
      ]
    }
    return h,t

def fresh_adversarial():
    h,t=good_transfer()
    assert score_case(h,t)["pass"] is True
    t2=dict(t);t2["transferred_primitive_fingerprint"]="prim:wrong"
    assert score_case(h,t2)["pass"] is False
    h2=dict(h);h2["surface_label_permutation_verified"]=False
    try: score_case(h2,t); raise AssertionError("surface randomization not enforced")
    except UnknownDomainScorerError: pass
    h3=dict(h);h3["domain_a_receipt_primitive_bindings"]={"R1":"prim:other"}
    assert score_case(h3,t)["pass"] is False
    trs=[{"leaf_id":TRANSFER,"case_id":f"T{i}","pass":True} for i in range(12)]
    absrows=[{"leaf_id":ABSTAIN,"case_id":f"A{i}","case_class":"IDENTIFIABLE","pass":True} for i in range(15)]
    try: aggregate(trs+absrows); raise AssertionError("class balance not enforced")
    except UnknownDomainScorerError: pass

if __name__=="__main__":
    exact_bytes(); family_freeze(); copied=run_copied_tests(); fresh_adversarial()
    print(json.dumps({
      "status":"PASS","exact_blob_count":3,"generated_cases":0,"candidate_bound":False,
      "copied_tests_passed":len(copied),"fresh_adversarial":"PASS","acceptance_credit_delta":0
    },sort_keys=True))
