#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"activation"

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

m=json.loads((ROOT/"ACTIVATION_EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    got=blob_sha(BASE/rel)
    assert got==expected,(rel,got,expected)

r3=json.loads((BASE/"canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json").read_text())
v8=json.loads((BASE/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json").read_text())
frontier=json.loads((BASE/"canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json").read_text())
terminal=json.loads((BASE/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())

ud=next(x for x in r3["compressed_residuals"] if x["predicate_id"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT")
assert ud["operative_learning_overlay"]=="UNIVERSAL_LEARNING_OPEN_WORLD_ROUTER_V4",ud
assert ud["operative_learning_overlay_verified"] is True,ud
assert "TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES" in ud["current_residual"],ud
assert "RUN_AND_INDEPENDENTLY_VERIFY_ONLY_THE_TWO_FROZEN_UNKNOWN_DOMAIN_DIRECT_ORACLE_LEAVES" in ud["next"],ud
assert r3["new_reality_units_consumed"]==0
assert r3["acceptance_credit_delta"]==0
assert r3["ownership_credit_delta"]==0

r3sha=m["exact_brain_blobs"]["canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json"]
v8sha=m["exact_brain_blobs"]["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"]
frontiersha=m["exact_brain_blobs"]["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"]

assert v8["authority"]["root3_compression"]["git_blob_sha"]==r3sha
assert frontier["authority"]["root3_residual_compression"]["git_blob_sha"]==r3sha
assert terminal["sources"]["root3_residual_compression_v1"]["git_blob_sha"]==r3sha
assert terminal["sources"]["root2_root3_minimum_execution_frontier_v1"]["git_blob_sha"]==frontiersha
assert terminal["sources"]["current_zero_reality_minimum_cut_v8"]["git_blob_sha"]==v8sha

truth=terminal["truth"]
assert truth["opus55_acceptance"]=="5/19_PASS__14/19_OPEN",truth
assert truth["opus55_verified_owned"]=="5/19_VERIFIED_OWNED_EQUAL_OR_BETTER__14/19_ACCEPTANCE_OPEN",truth
assert truth["achieved"] is False

src=terminal["sources"]["universal_learning_open_world_v4"]
assert src["status"].endswith("ZERO_ACCEPTANCE_AND_OWNERSHIP_CREDIT"),src
assert terminal["status"]=="ACTIVE_FAIL_CLOSED__TERMINAL_GOAL_NOT_ACHIEVED"

print(json.dumps({
  "schema":"PROJECT_BRAIN_UNIVERSAL_LEARNING_V4_ACTIVATION_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__ROOT3_V4_OPERATIVE_OVERLAY__HASH_CHAIN_REBOUND__TWO_LEAVES_OPEN__5_OF_19_UNCHANGED__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_activation_blob_identities":True,
    "unknown_domain_overlay_is_v4":True,
    "two_frozen_unknown_domain_leaves_remain_open":True,
    "root3_to_cut_v8_hash_binding":True,
    "root3_to_minimum_frontier_hash_binding":True,
    "terminal_authority_hash_bindings":True,
    "acceptance_count_unchanged":True,
    "ownership_count_unchanged":True,
    "zero_reality_and_zero_credit_preserved":True
  }
},indent=2,sort_keys=True))
