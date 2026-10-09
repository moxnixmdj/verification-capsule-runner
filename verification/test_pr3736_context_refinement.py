from __future__ import annotations
import importlib.util, pathlib, sys, types

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/"source"

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

proof=types.ModuleType("canonical.runtime.proof_carrying_domain_mapping_v1")
proof.resolve=lambda *a,**k: {"status":"UNRESOLVED","candidate_evaluations":[],"semantic_truth_authority":False}
sys.modules["canonical.runtime.proof_carrying_domain_mapping_v1"]=proof

ctx_spec=importlib.util.spec_from_file_location(
 "canonical.runtime.source_aligned_regcap_context_proof_v1",
 SRC/"source_aligned_regcap_context_proof_v1.py")
ctx=importlib.util.module_from_spec(ctx_spec)
sys.modules[ctx_spec.name]=ctx
ctx_spec.loader.exec_module(ctx)
setattr(runtime,"source_aligned_regcap_context_proof_v1",ctx)

dm_spec=importlib.util.spec_from_file_location(
 "canonical.runtime.domain_mapping_truth_certificate_v1",
 SRC/"domain_mapping_truth_certificate_v1.py")
dm=importlib.util.module_from_spec(dm_spec)
sys.modules[dm_spec.name]=dm
dm_spec.loader.exec_module(dm)

text="a 2.5% buffer comprised of Common Equity Tier 1 (CET1) above the regulatory minimum capital requirement"
payload={
 "truth_kind":"DOMAIN_MAPPING_RELATION","predicate_id":"caller-id","raw_span":text,
 "source_id":"doc:regcap","scope_id":"finance:regulatory-capital:2026",
 "target_concept_id":"REGCAP::CCOB","required_relation":"SEMANTIC_IDENTITY",
 "candidate_concepts":[{"concept_id":"REGCAP::CCOB","surface":"capital conservation buffer","required_atoms":[],"forbidden_atoms":[]}],
 "relation_problems":{"REGCAP::CCOB":{"required_relation":"SEMANTIC_IDENTITY"}}
}
out=dm.evaluate(payload)
assert out["pass"] is False, out
assert out["predicate_truth"]=="UNKNOWN", out
assert out["truthful_precommitment_observation"] is False, out
ref=out["authenticated_context_refinement"]
assert ref["semantic_truth_authority"] is True, ref
assert set(ref["proved_atom_ids"])=={
 "AMOUNT::2.5_PERCENT","COMPOSITION::CET1","POSITION::ABOVE_REGULATORY_MINIMUM"
}, ref
assert ref["concept_identity_claimed"] is False, ref
assert out["next_information_request"]["kind"]=="REUSE_AUTHENTICATED_CONTEXT_FACTS_FOR_DOMAIN_MAPPING", out
assert out["terminal_authority"] is False, out
print("PASS__PR3736_CONTEXTUAL_REFINEMENT")
