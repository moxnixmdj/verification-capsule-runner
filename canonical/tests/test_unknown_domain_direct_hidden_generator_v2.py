from __future__ import annotations

import json

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2


def fixture(beacon="fixture-beacon-00000001"):
    return v2.generate_qualification_fixture_population(beacon=beacon)


def test_v2_preserves_frozen_population_counts_and_classes():
    out=fixture()
    assert out["case_count"]==27
    assert sum(x["leaf_id"]==v1.TRANSFER for x in out["visible_cases"])==12
    hidden=[x for x in out["hidden_records"] if x["leaf_id"]==v1.ABSTAIN]
    counts={x:0 for x in v1.ABSTAIN_CLASSES}
    for row in hidden: counts[row["identifiability_status"]]+=1
    assert counts=={"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5}


def test_different_qualification_beacons_resample_numeric_cases():
    a=fixture("fixture-beacon-00000001")
    b=fixture("fixture-beacon-00000002")
    assert a["visible_packet_digest"]!=b["visible_packet_digest"]
    at=next(x for x in a["visible_cases"] if x["leaf_id"]==v1.TRANSFER)
    bt=next(x for x in b["visible_cases"] if x["leaf_id"]==v1.TRANSFER)
    assert at["domain_a"]["earned_receipts"][0]["normalized_primitive_program"] != bt["domain_a"]["earned_receipts"][0]["normalized_primitive_program"]
    assert at["domain_b"]["tasks"] != bt["domain_b"]["tasks"]


def test_domain_a_and_b_observation_values_are_independently_resampled():
    out=fixture()
    for case in out["visible_cases"]:
        if case["leaf_id"]!=v1.TRANSFER: continue
        arows=case["domain_a"]["tasks"]
        brows=case["domain_b"]["tasks"]
        assert arows!=brows


def test_visible_packet_has_no_hidden_family_or_mapping_truth():
    out=fixture()
    text=json.dumps(out["visible_cases"],sort_keys=True)
    for literal in v1.PRIMITIVE_FAMILIES:
        assert literal not in text
    for forbidden in ("primitive_family","domain_mapping","transfer_relevant_feature_ids","distractor_feature_ids","identifiability_status","minimum_discriminator_id","allowed_probe_outcome_table"):
        assert f'"{forbidden}"' not in text


def test_public_rows_preserve_deliberate_mapping_ambiguity_but_probe_breaks_it():
    out=fixture()
    hidden={x["case_id"]:x for x in out["hidden_records"]}
    for case in out["visible_cases"]:
        if case["leaf_id"]!=v1.TRANSFER: continue
        h=hidden[case["case_id"]]
        relevant=h["transfer_relevant_feature_ids"]
        distractors=h["distractor_feature_ids"]
        public=case["domain_b"]["tasks"]
        for i,d in enumerate(distractors):
            r=relevant[i%len(relevant)]
            assert all(row["inputs"][d]==row["inputs"][r] for row in public)
        p=case["domain_b"]["allowed_probes"][0]["probe_id"]
        probe=h["allowed_probe_outcome_table"][p]
        assert all(probe["inputs"][d]!=probe["inputs"][relevant[i%len(relevant)]] for i,d in enumerate(distractors))


def test_step_and_sign_cases_have_nontrivial_identifying_variation():
    out=fixture()
    hidden={x["case_id"]:x for x in out["hidden_records"]}
    for case in out["visible_cases"]:
        if case["leaf_id"]!=v1.TRANSFER: continue
        h=hidden[case["case_id"]]
        op=h["latent_primitive_program"]["op"]
        ys=[row["terminal_consequence"] for row in case["domain_b"]["tasks"]]
        if op in {"SIGN","STEP"}:
            assert len(set(ys))>=2


def test_production_authority_gate_remains_v1_load_bearing():
    authority={
      "active":False,
      "target_predicate":v1.TARGET_PREDICATE,
      "authorized_leaves":[v1.TRANSFER,v1.ABSTAIN],
      "predicate_local_fresh_reality":True,
      "global_fresh_reality":False,
      "one_use_claim_created":True,
      "one_use_claim_id":"x",
      "incremental_spend_usd":0,
    }
    try:
        v2.generate_production_population(beacon="0123456789abcdef",evaluator_secret=b"x"*32,authority=authority)
        raise AssertionError("production generation unexpectedly authorized")
    except v1.UnknownDomainGeneratorError as exc:
        assert "PREDICATE_LOCAL_AUTHORITY_NOT_ACTIVE" in str(exc)


def test_same_qualification_beacon_is_deterministic():
    a=fixture("fixture-beacon-00000009")
    b=fixture("fixture-beacon-00000009")
    assert a["visible_packet_digest"]==b["visible_packet_digest"]
    assert a["hidden_packet_digest"]==b["hidden_packet_digest"]
