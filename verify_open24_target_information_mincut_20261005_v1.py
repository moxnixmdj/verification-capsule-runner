#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

EXPECTED = {
 "registry": ("subjects/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json","562536d9ba3f245a6bd24490a1eb3b30f27e0c3a"),
 "evidence": ("subjects/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json","a3fd20e58fdbd9b86278b7de0c245de3063dce27"),
 "cut": ("subjects/OPUS55_OPEN24_TARGET_INFORMATION_MINCUT_20261005_V1.json","4ce73364339f4982609ae805bef976b259617642"),
}
def blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load_exact(key):
    p, expected = EXPECTED[key]
    raw=Path(p).read_bytes()
    actual=blob_sha(raw)
    assert actual==expected, (key,actual,expected)
    return json.loads(raw)
registry=load_exact("registry")
evidence=load_exact("evidence")
cut=load_exact("cut")

preds=registry["predicates"]
assert len(preds)==38
by_id={p["id"]:p for p in preds}
assert len(by_id)==38
claims=evidence["claims"]
claim_by_id={c["predicate_id"]:c for c in claims}
assert len(claim_by_id)==38
proved={pid for pid,c in claim_by_id.items() if c.get("state")=="PROVED"}
open_ids=set(by_id)-proved
assert len(proved)==14, len(proved)
assert len(open_ids)==24, len(open_ids)

# Independently derive the target-information classes from the frozen registry kinds.
fixed={pid for pid in open_ids if by_id[pid]["kind"]=="PUBLIC_FIXED_BAR"}
matched_noninf={pid for pid in open_ids if by_id[pid]["kind"]=="MATCHED_NONINFERIORITY"}
direct_or_dependency={pid for pid in open_ids if by_id[pid]["kind"] in {"DIRECT_SCOPE_AUDIT","DEPENDENCY_PROOF"}}
matched_scope={pid for pid in open_ids if by_id[pid]["kind"]=="MATCHED_SCOPE_AUDIT"}
zero_critical={pid for pid in matched_scope if "ZERO_CRITICAL" in pid}
matched_scope_relative=matched_scope-zero_critical
derived_target_free=direct_or_dependency|zero_critical
derived_relative=matched_noninf|matched_scope_relative

part=cut["exact_open24_partition"]
candidate_fixed=set(part["frozen_public_threshold_no_fresh_target_output"])
candidate_free=set(part["target_free_structural_acceptance"])
candidate_relative=set(part["target_relative_or_matched_unless_stronger_proof"])

assert candidate_fixed==fixed, (candidate_fixed^fixed)
assert candidate_free==derived_target_free, (candidate_free^derived_target_free)
assert candidate_relative==derived_relative, (candidate_relative^derived_relative)
assert candidate_fixed|candidate_free|candidate_relative==open_ids
assert not (candidate_fixed&candidate_free)
assert not (candidate_fixed&candidate_relative)
assert not (candidate_free&candidate_relative)
assert (len(candidate_fixed),len(candidate_free),len(candidate_relative))==(14,4,6)

# Semantic sanity: target-free structural acceptance text must not require Opus output.
for pid in candidate_free:
    text=by_id[pid]["acceptance"].lower()
    assert "opus" not in text, (pid,text)

# The relative class must be exactly all open matched-noninferiority plus non-zero matched-scope audits.
for pid in candidate_relative:
    kind=by_id[pid]["kind"]
    assert kind in {"MATCHED_NONINFERIORITY","MATCHED_SCOPE_AUDIT"}, (pid,kind)
    if kind=="MATCHED_SCOPE_AUDIT":
        assert "ZERO_CRITICAL" not in pid

# Fixed bars are frozen target-derived thresholds; fresh Opus behavior is not load-bearing once frozen.
for pid in candidate_fixed:
    assert by_id[pid]["kind"]=="PUBLIC_FIXED_BAR"
    assert ">=" in by_id[pid]["acceptance"]

# Fail closed against overclaim.
assert cut["scheduling_authority"] is False
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False
assert cut["fresh_reality_authority"] is False
assert cut["independent_verification_required"] is True
for k,v in cut["accounting"].items():
    if k.endswith("_delta") or k in {"incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed"}:
        assert v==0, (k,v)

receipt={
 "schema":"PROJECT_BRAIN_OPEN24_TARGET_INFORMATION_MINCUT_INDEPENDENT_VERIFICATION_20261005_V1",
 "result":"PASS__EXACT_OPEN24_PARTITION_DERIVED_FROM_FROZEN_REGISTRY",
 "subject_git_blob_sha":EXPECTED["cut"][1],
 "registry_git_blob_sha":EXPECTED["registry"][1],
 "evidence_git_blob_sha":EXPECTED["evidence"][1],
 "proved_atomic":len(proved),
 "open_atomic":len(open_ids),
 "partition":{"fixed_public_bar":14,"target_free_structural":4,"target_relative_or_matched":6},
 "fresh_target_output_independent_count":18,
 "candidate_target_specific_information_remainder_count":6,
 "scope":"VERIFIES_CURRENT_14_24_IDENTITY_AND_TARGET_INFORMATION_CLASSIFICATION_ONLY__DOES_NOT_CLOSE_ANY_PREDICATE_OR_PROVE_THE_SIX_IRREDUCIBLY_REQUIRE_OPUS_OUTPUT",
 "incremental_spend_usd":0,
 "new_reality_units_consumed":0,
 "terminal_cases_consumed":0
}
Path("results").mkdir(exist_ok=True)
Path("results/open24_target_information_mincut_verification_20261005_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,indent=2,sort_keys=True))
