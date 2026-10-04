from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

from canonical.runtime.unknown_domain_direct_execution_harness_v1 import (
    UnknownDomainHarnessError,
    execute_case,
)
from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import TRANSFER

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
  "canonical/tests/test_unknown_domain_direct_execution_harness_v1.py":"f437be256fd4bf48cd1b276bf4c223599abecf84",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_FREEZE_V1.json":"3e3a87962c13ad4c76621508763fab74df25cb44",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
  "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V1.json":"26108d0d06f7a308c3eaf4b9821ff0c4551dcda3",
}


def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def exact_bytes():
    for path,expected in EXPECTED.items():
        got=git_blob((ROOT/path).read_bytes())
        assert got==expected,(path,got,expected)


def copied_tests():
    mod=importlib.import_module("canonical.tests.test_unknown_domain_direct_execution_harness_v1")
    names=sorted(n for n in dir(mod) if n.startswith("test_") and callable(getattr(mod,n)))
    assert names
    for name in names:
        getattr(mod,name)()
    return names


def governance():
    d=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_FREEZE_V1.json").read_text())
    assert d["accounting"]["generated_production_case_count"]==0
    assert d["accounting"]["terminal_cases_consumed"]==0
    assert d["accounting"]["new_reality_units_consumed"]==0
    assert d["candidate_interface"]=="step(case_visible, transcript) -> action"
    assert "MAX_TRANSFER_PROBES_EQUALS_2" in d["interaction_rules"]
    assert "NO_BRAIN_CANDIDATE_QUALIFICATION" in d["hard_nonclaims"]


def fresh_adversarial():
    visible={
      "case_id":"ADV","leaf_id":TRANSFER,
      "domain_a":{"tasks":[],"earned_receipts":[]},
      "domain_b":{
        "tasks":[],"query_inputs":{},
        "allowed_probes":[{"probe_id":"P1","argument_schema":{},"cost":1}],
        "tool_metadata":{},
      },
      "decision_requirement":"x",
    }
    hidden={
      "case_id":"ADV","leaf_id":TRANSFER,"gold_terminal_consequence":"GO",
      "domain_a_earned_receipt_ids":["R1"],"full_rediscovery_probe_floor":3,
      "latent_primitive_fingerprint":"prim:x",
      "domain_a_receipt_primitive_bindings":{"R1":"prim:x"},
      "surface_label_permutation_verified":True,"domain_vocabularies_disjoint":True,
      "transfer_relevant_feature_ids":["F1"],"distractor_feature_ids":["D1","D2"],
      "allowed_probe_outcome_table":{"P1":{"inputs":{"F1":1},"terminal_consequence":"GO"}},
    }
    saw=[]
    def candidate(case,transcript):
        saw.append((dict(case),tuple(transcript)))
        if not transcript:
            return {"type":"REQUEST_PROBE","probe_id":"P1"}
        return {
          "type":"CONCLUDE","terminal_consequence":"GO",
          "domain_a_source_receipt_ids":["R1"],
          "transferred_primitive_fingerprint":"prim:x",
          "support_feature_ids":["F1"],
          "negative_transfer_rejected_feature_ids":["D1","D2"],
          "mapping_basis":"STRUCTURAL_EQUIVALENCE",
          "evidence_provenance":[
            {"evidence_id":"R1","source":"A","receipt":"r"},
            {"evidence_id":"F1","source":"B","receipt":"r"},
            {"evidence_id":"D1","source":"B","receipt":"r"},
            {"evidence_id":"D2","source":"B","receipt":"r"},
          ],
        }
    out=execute_case(candidate_step=candidate,case_visible=visible,hidden_record=hidden)
    assert out["scorer_result"]["pass"] is True
    assert saw[0][1]==()
    assert "latent_primitive_fingerprint" not in json.dumps(saw[0][0],sort_keys=True)
    assert saw[1][1][0]["requested_probe_id"]=="P1"


if __name__=="__main__":
    exact_bytes()
    governance()
    names=copied_tests()
    fresh_adversarial()
    print(json.dumps({
      "status":"PASS",
      "exact_blob_count":len(EXPECTED),
      "copied_harness_tests_passed":len(names),
      "fresh_adversarial":"PASS",
      "generated_production_cases":0,
      "candidate_bound":False,
      "acceptance_credit_delta":0,
    },sort_keys=True))
