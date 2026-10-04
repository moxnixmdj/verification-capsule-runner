from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

from canonical.runtime.unknown_domain_direct_hidden_generator_v1 import (
    ABSTAIN,
    TRANSFER,
    UnknownDomainGeneratorError,
    generate_production_population,
    generate_test_fixture_population,
)

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
  "canonical/tests/test_unknown_domain_direct_hidden_generator_v1.py":"e81e92e6d68b3de008b974e956437cc90b301be4",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V1.json":"26108d0d06f7a308c3eaf4b9821ff0c4551dcda3",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
  "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
}


def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def exact_bytes():
    for path,expected in EXPECTED.items():
        got=git_blob((ROOT/path).read_bytes())
        assert got==expected,(path,got,expected)


def governance_boundary():
    d=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V1.json").read_text())
    assert d["accounting"]["generated_production_case_count"]==0
    assert d["accounting"]["terminal_cases_consumed"]==0
    assert d["accounting"]["new_reality_units_consumed"]==0
    assert d["accounting"]["incremental_spend_usd"]==0
    assert d["evaluator_authority"]["independent_verification_run_id"]==37196729520
    assert d["evaluator_authority"]["independent_verification_conclusion"]=="success"
    assert d["production_population"]["transfer_cases"]==12
    assert d["production_population"]["abstention_cases"]==15
    assert d["production_population"]["abstention_balance"]=={
      "IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5
    }
    assert "NO_PRODUCTION_CASE_IDS_OR_CONTENT_EXIST_IN_THIS_FREEZE" in d["hard_nonclaims"]


def copied_tests():
    mod=importlib.import_module("canonical.tests.test_unknown_domain_direct_hidden_generator_v1")
    names=sorted(n for n in dir(mod) if n.startswith("test_") and callable(getattr(mod,n)))
    assert names
    for name in names:
        getattr(mod,name)()
    return names


def fresh_adversarial():
    a=generate_test_fixture_population()
    b=generate_test_fixture_population()
    assert a["visible_packet_digest"]==b["visible_packet_digest"]
    assert a["hidden_packet_digest"]==b["hidden_packet_digest"]

    visible_text=json.dumps(a["visible_cases"],sort_keys=True)
    for literal in (
      "ORDER_PRESERVING_TRANSFORM","PARITY_OR_SIGN_INVARIANT","CONSERVATION_RELATION",
      "MONOTONE_CAUSAL_EDGE","COMPOSITIONAL_REWRITE","THRESHOLD_OR_PARTITION_INVARIANT",
      "latent_primitive_fingerprint","domain_mapping","distractor_feature_ids",
      "identifiability_status","minimum_discriminator_id",
    ):
        assert literal not in visible_text,literal

    hidden={x["case_id"]:x for x in a["hidden_records"]}
    for case in a["visible_cases"]:
        if case["leaf_id"]==TRANSFER:
            h=hidden[case["case_id"]]
            receipt=case["domain_a"]["earned_receipts"][0]
            assert receipt["primitive_fingerprint"]==h["latent_primitive_fingerprint"]
            assert receipt["source_role_binding"]
            assert not set(receipt["source_role_binding"].values()) & set(h["transfer_relevant_feature_ids"])
        elif case["leaf_id"]==ABSTAIN:
            assert "identifiability_status" not in case

    bad={
      "active":True,
      "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
      "authorized_leaves":[TRANSFER,ABSTAIN],
      "predicate_local_fresh_reality":True,
      "global_fresh_reality":True,
      "one_use_claim_created":True,
      "one_use_claim_id":"bad-global",
      "incremental_spend_usd":0,
    }
    try:
        generate_production_population(
          beacon="0123456789abcdef",
          evaluator_secret=b"x"*32,
          authority=bad,
        )
        raise AssertionError("global authority leak accepted")
    except UnknownDomainGeneratorError as exc:
        assert "GLOBAL_FRESH_REALITY_MUST_REMAIN_FALSE" in str(exc)


if __name__=="__main__":
    exact_bytes()
    governance_boundary()
    names=copied_tests()
    fresh_adversarial()
    print(json.dumps({
      "status":"PASS",
      "exact_blob_count":len(EXPECTED),
      "copied_generator_tests_passed":len(names),
      "fresh_adversarial":"PASS",
      "generated_production_cases":0,
      "candidate_bound":False,
      "acceptance_credit_delta":0,
    },sort_keys=True))
