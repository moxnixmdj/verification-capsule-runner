#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "v3":("subjects/retrieval_v3_activation.json","4fde285b62a3a84e7f12852d8600aecfc01bab81"),
 "v2":("subjects/retrieval_v2_activation.json","c916c095cfb52b4b3d8dd863dfb0be0f05529f2e"),
 "components":("subjects/retrieval_v3_component_verification.json","6e2f64c6664c175cd699e245e73f61338838abd3"),
}
def sha(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]
 q=ROOT/p
 actual=sha(q)
 assert actual==s,(k,actual,s)
 return json.loads(q.read_text())

v3=load("v3"); v2=load("v2"); comp=load("components")

assert v3["schema"]=="PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1"
assert v3["base_retrieval_authority"]["git_blob_sha"]==FILES["v2"][1]
assert v3["base_retrieval_authority"]["rule"]=="V2_REMAINS_MANDATORY_AND_IS_NOT_WEAKENED"
assert v3["v3_verified_extension"]["verification_git_blob_sha"]==FILES["components"][1]

expected_components={
 "wikidata_language_bridge":"1698a02f372a7ed6446d1519d9385dcff8619786",
 "adaptive_query_expansion":"180cce242914a0b7c0925c50579dd1e336b9ef35",
 "public_source_federation":"3f69b3e8371fe3e5abc173c6c9fe17e9003a938b",
 "adversarial_recall_benchmark":"947f09640bc6e8ca98c4e3c2c975ab87071f6f1f",
}
for key,blob in expected_components.items():
 assert v3["v3_verified_extension"][key]["git_blob_sha"]==blob,(key,v3["v3_verified_extension"][key])

assert comp["independent_runner"]["conclusion"]=="success"
ver=comp["verified"]
assert ver["wikidata_cross_script_candidate_generation"] is True
assert ver["wikidata_no_match_preserves_unknown"] is True
assert ver["adaptive_unicode_query_evolution"] is True
assert ver["orthogonal_public_source_federation"] is True
assert ver["declared_finite_observable_adversarial_recall"]==1.0
assert ver["declared_finite_observable_adversarial_misses"]==0
assert ver["unbridgeable_artifact_preserves_unknown"] is True
assert ver["open_world_completeness_claim"] is False

protocol=v3["mandatory_epoch_protocol"]
required=[
 "RUN_V2_EXACT_RESIDUAL_COMPILER_AND_VERIFIED_BACKENDS",
 "STOP_IMMEDIATELY_IF_AN_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS_CLOSES_THE_RESIDUAL",
 "OTHERWISE_GENERATE_ZERO_COST_MULTILINGUAL_CANDIDATE_VARIANTS_FROM_EXTERNAL_WIKIDATA_LABELS_AND_ALIASES_WHERE_AVAILABLE",
 "RUN_ADAPTIVE_UNICODE_QUERY_EVOLUTION_USING_TECHNICAL_ANCHORS_AND_PRIOR_CANDIDATE_TERMS",
 "COMPILE_ORTHOGONAL_PUBLIC_SOURCE_FEDERATION_REQUESTS",
 "CLASSIFY_EVERY_RESULT_BY_PROVENANCE_AND_ADMISSIBILITY",
 "IF_NO_SUFFICIENT_WITNESS_EXISTS_PRESERVE_UNKNOWN_AND_CONTENT_ADDRESS_THE_CONSUMED_SOURCE_EPOCH",
]
for item in required:
 assert item in protocol,item

assert len(v3["source_federation_classes"])==14
assert v3["stop_rules"]["verified_sufficient_witness"]=="STOP_AND_RUN_ACCEPTANCE_REDUCER"
assert v3["stop_rules"]["no_witness_and_scope_not_complete"]=="UNKNOWN__DO_NOT_INFER_NONEXISTENCE"
assert "NO_SOURCE_EPOCH_EXHAUSTION_BEFORE_V3_EXPANSION_UNLESS_A_VERIFIED_SUFFICIENT_WITNESS_ALREADY_STOPPED_THE_SEARCH" in v3["hard_rules"]
assert "FINITE_ADVERSARIAL_RECALL_1_DOES_NOT_IMPLY_OPEN_WORLD_COMPLETENESS" in v3["hard_rules"]
assert "UNBRIDGEABLE_OR_INACCESSIBLE_MATERIAL_REMAINS_UNKNOWN" in v3["hard_rules"]
assert "NO_RESULT_IS_NOT_NONEXISTENCE" in v3["hard_rules"]
assert v3["capability_credit_delta"]==0 and v3["family_credit_delta"]==0
assert v3["execution_authority"] is False and v3["promotion_authority"] is False

# V3 is strictly additive: V2's fail-closed state and no-replay law remain present.
assert v2["operational_policy"]["current_state"]=="UNKNOWN_SCOPE_RELATION__STRICT_ACCEPTANCE_OPEN"
assert v2["operational_policy"]["repeat_v1_source_epoch"] is False
assert v2["operational_policy"]["repeat_v2_github_source_epoch"] is False
assert "NO_RESULT_IS_NOT_NONEXISTENCE" in v2["hard_rules"]

print("RETRIEVAL_V3_ACTIVATION_VERIFIED")
print(json.dumps({
 "exact_blobs":{k:v[1] for k,v in FILES.items()},
 "v2_preserved":True,
 "finite_observable_recall":1.0,
 "unbridgeable_unknown":True,
 "open_world_completeness_claim":False,
 "zero_credit":True
},sort_keys=True))
