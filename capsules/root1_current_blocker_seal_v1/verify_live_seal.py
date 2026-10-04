#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())

def git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def subpath(rel:str)->Path:
    if rel.startswith("canonical/runtime/") or rel.startswith("canonical/tests/") or rel.startswith("canonical/governance/ROOT1_CURRENT_"):
        return ROOT/"subject"/rel
    return ROOT/"fixtures"/rel

for rel,expected in EXPECTED["exact_blobs"].items():
    got=git_blob_sha(subpath(rel))
    assert got==expected,(rel,got,expected)

runtime_path=ROOT/"subject/canonical/runtime/root1_current_blocker_classification_seal_v1.py"
spec=importlib.util.spec_from_file_location("root1_seal",runtime_path)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

def load(rel):
    return json.loads(subpath(rel).read_text())

env=load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json")
manifest=load("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
ledger=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
gov=load("canonical/governance/ROOT1_CURRENT_BLOCKER_CLASSIFICATION_SEAL_V1.json")

result=mod.compute_current_root1_blocker_seal(
    target_envelope=env,
    terminal_manifest=manifest,
    predicate_registry=registry,
    evidence_ledger=ledger,
    root_state=root,
)

assert result["target_family_count"]==19,result
assert result["atomic_predicate_count"]==38,result
assert result["proved_predicate_count"]==12,result
assert result["unresolved_predicate_count"]==26,result
assert result["root2_only_count"]==16,result
assert result["root3_only_count"]==7,result
assert result["root2_and_root3_count"]==3,result
assert result["root1_positive_gap_count"]==0,result
assert result["root1_current_blocker_residual_count"]==0,result
assert result["root1_current_blocker_residual_ids"]==[],result
assert result["current_root1_classification_sealed"] is True,result
assert result["current_root1_active"] is False,result
assert result["seal_scope"]=="CURRENT_FROZEN_TERMINAL_ENVELOPE_AND_CURRENT_EVIDENCE_LEDGER_ONLY"

assert env["target_family_count"]==19
assert env["target_rule"]=="USEFUL_BEHAVIOR_NOT_INTERNAL_IMPLEMENTATION"
assert manifest["expected_family_count"]==manifest["actual_family_count"]==19
for key in (
    "uncontracted_required_behaviors",
    "unproved_required_behaviors",
    "donor_dependent_required_behaviors",
    "unresolved_verifier_mutations",
    "unresolved_composition_failures",
    "contaminated_promotion_evidence",
    "resource_or_authority_violations",
):
    assert manifest["counters"][key]==0,(key,manifest["counters"][key])

assert root["current_acceptance"]=={
    "accepted_families":5,
    "open_families":14,
    "proved_atomic":12,
    "unresolved_atomic":26,
    "total_families":19,
    "total_atomic":38,
    "terminal":False,
}
assert root["roots"]["root_1_capability_missing"]["current_positive_root1_blockers"]==[]
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0

assert gov["theorem"]["equation"]=="26 = 16 + 7 + 3"
assert gov["theorem"]["root1_current_residual"]==0
assert gov["accounting"]=={
    "acceptance_credit_delta":0,
    "family_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0,
    "new_reality_units_consumed":0,
    "incremental_spend_usd":0,
}

# Counterexample 1: remove one unresolved predicate from all R2/R3 buckets.
bad=copy.deepcopy(root)
victim=bad["current_residual_root_partition"]["root2_only"].pop()
bad["current_residual_root_partition"]["root2_only_count"]-=1
try:
    mod.compute_current_root1_blocker_seal(
        target_envelope=env,terminal_manifest=manifest,predicate_registry=registry,
        evidence_ledger=ledger,root_state=bad)
except mod.Root1SealError as exc:
    assert "ROOT_PARTITION_NOT_EXHAUSTIVE" in str(exc),exc
else:
    raise AssertionError("UNCLASSIFIED_UNRESOLVED_PREDICATE_DID_NOT_BREAK_SEAL:"+victim)

# Counterexample 2: insert a constructive Root1 gap.
bad=copy.deepcopy(root)
bad["current_residual_root_partition"]["root1_positive_gap_count"]=1
try:
    mod.compute_current_root1_blocker_seal(
        target_envelope=env,terminal_manifest=manifest,predicate_registry=registry,
        evidence_ledger=ledger,root_state=bad)
except mod.Root1SealError as exc:
    assert "ROOT1_POSITIVE_GAP_COUNT_NONZERO" in str(exc),exc
else:
    raise AssertionError("POSITIVE_ROOT1_GAP_DID_NOT_BREAK_SEAL")

# Counterexample 3: lie that a proved predicate is scope-complete when fixture says otherwise.
bad=copy.deepcopy(ledger)
proved=next(x for x in bad["claims"] if x.get("state")=="PROVED")
proved["scope_complete"]=False
try:
    mod.compute_current_root1_blocker_seal(
        target_envelope=env,terminal_manifest=manifest,predicate_registry=registry,
        evidence_ledger=bad,root_state=root)
except mod.Root1SealError as exc:
    assert "PROVED_WITHOUT_SCOPE_COMPLETE" in str(exc),exc
else:
    raise AssertionError("UNSCOPE_COMPLETE_PROVED_CLAIM_DID_NOT_BREAK_SEAL")

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT1_CURRENT_BLOCKER_CLASSIFICATION_SEAL_PUBLIC_RUNNER_RESULT",
  "status":"PASS__EXACT_LIVE_19_FAMILY_38_PREDICATE_12_PROVED_26_UNRESOLVED__26_EQUALS_16_PLUS_7_PLUS_3__ROOT1_RESIDUAL_ZERO__COUNTEREXAMPLES_REJECTED__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_subject_and_fixture_blobs":True,
    "target_family_set_exact_19":True,
    "manifest_required_behavior_counters_zero":True,
    "atomic_registry_exact_38":True,
    "proved_scope_complete_exact_12":True,
    "unresolved_exact_26":True,
    "root2_only_exact_16":True,
    "root3_only_exact_7":True,
    "root2_and_root3_exact_3":True,
    "unresolved_union_equals_root2_root3_partition":True,
    "root1_positive_gap_count_zero":True,
    "root1_current_residual_zero":True,
    "unclassified_predicate_breaks_seal":True,
    "constructive_root1_gap_breaks_seal":True,
    "unscope_complete_proof_breaks_seal":True,
    "future_root1_reopen_preserved":True,
    "zero_terminal_credit":True
  },
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "execution_authority":False,
  "promotion_authority":False,
  "fresh_reality_authority":False
},indent=2,sort_keys=True))
