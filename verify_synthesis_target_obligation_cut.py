#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

ROOT=Path("subject/synthesis_target_obligation_cut")
FILES={
"sep":("TARGET_BEHAVIOR_MECHANISM_SCOPE_SEPARATION_20261005_V1.json","251cac9c9f7892e26ca90f2f5118f31e1df02099"),
"collision":("SYNTHESIS_LEAF_SCOPE_CONCURRENCY_CONFLICT_RECONCILIATION_20261005_V1.json","4b1b9c7149eb040447b8dd1665366eccfbca60f4"),
"cert":("SYNTHESIS_SCOPE_CERTIFICATE_V1.json","dea9028f92f111ee3c8be71615fa4b02e8a8bfb6"),
"protocols":("OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json","62394e5b7d221ec9f69c3458f669e40e253a9d09"),
"frontier":("SIX_BENCHMARK_PROXY_SCOPE_REPAIR_FRONTIER_V3.json","2442af340f6445c1c8fbba7d770461a4e20a0378"),
"envelope":("OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json","661a57f839101fbf54c7e4edc76166c65ce9327d"),
"candidate":("SYNTHESIS_WHOLE_LEAF_TARGET_OBLIGATION_CUT_20261005_V1.json","6169d6ef3f69b5ad66d2844006e7e9550bfc1c6c"),
}
DIMS={
"claim-to-source fidelity","required evidence coverage","uncertainty/disagreement preservation",
"audience adaptation","format/style constraints","compression without decision-relevant loss"
}
FANOUT={"PROFESSIONAL_KNOWLEDGE_WORK","MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING","AGENTIC_SCIENTIFIC_RESEARCH"}

def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

docs={}
for k,(name,sha) in FILES.items():
    data=(ROOT/name).read_bytes()
    got=git_blob(data)
    assert got==sha,(k,got,sha)
    docs[k]=json.loads(data)

env={x["id"]:x for x in docs["envelope"]["families"]}
expected_behaviors={
"PROFESSIONAL_KNOWLEDGE_WORK":"Produce high-quality professional work products and complete multi-hour/multi-stage office tasks.",
"MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING":"Solve difficult expert-level questions across domains with search/code/tools.",
"AGENTIC_SCIENTIFIC_RESEARCH":"Use scientific software, tools, analysis and iterative reasoning to solve long-horizon research/technical tasks.",
"COMMUNICATION_AND_SYNTHESIS":"Communicate clearly, prioritize what matters, follow writing rules and synthesize complex work over long sessions.",
}
for fam,text in expected_behaviors.items():
    assert env[fam]["useful_behavior"]==text

# Formal non-entailment rule: to refute T => M, one admissible T-realization without M is sufficient.
# These witnesses satisfy the broad observable family sentence while not requiring the exact
# EVIDENCE_TO_AUDIENCE_SYNTHESIS_001 input/action contract.
countermodels={
"PROFESSIONAL_KNOWLEDGE_WORK":{
    "T_realization":"Complete a multi-stage spreadsheet cleanup and formula repair whose acceptance is file correctness.",
    "M_absent":"No verified-evidence-unit/provenance/audience synthesis transform is required."
},
"MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING":{
    "T_realization":"Solve a closed expert numerical question with search/code/tools and return the exact scalar answer.",
    "M_absent":"No audience-adapted evidence synthesis deliverable is required."
},
"AGENTIC_SCIENTIFIC_RESEARCH":{
    "T_realization":"Use scientific software iteratively to compute and validate a requested numerical technical result.",
    "M_absent":"No evidence-to-audience synthesis transform is required by that task."
},
}
assert set(countermodels)==FANOUT

edges=[e for e in docs["sep"]["current_frontier_audit"]["edges"] if e.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]
assert {e["family"] for e in edges}==FANOUT
assert all(e.get("mandatory_from_registry_incidence") is False for e in edges)

p=next(x for x in docs["protocols"]["protocols"] if x["family"]=="COMMUNICATION_AND_SYNTHESIS")
assert p["proof_mode"]=="MATCHED_GROUNDED_SYNTHESIS_NONINFERIORITY"
assert set(p["task_dimensions"])==DIMS

cert=docs["cert"]
assert cert["target_scope_id"]=="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
assert cert["coverage_complete"] is True
assert cert["coverage_relation"]=="EXACT_UNION"
assert cert["scope_relation"]=="PROVEN_STRONGER"
assert len(cert["children"])==6
assert all(c["formal_completeness"] is True and c["all_admissible_target_inputs_proved"] is True for c in cert["children"])

collision=docs["collision"]["fail_closed_truth"]
assert collision["whole_behavior_leaf_input_domain_scope_complete"] is False
assert collision["predicate_level_root3_scope_relation_closed"] is True
assert collision["synthesis_matched_performance_open"] is True

roots=docs["frontier"]["active_registry_scope_repair_roots"]
syn=[x for x in roots if x["id"]=="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"]
assert len(syn)==1 and set(syn[0]["fanout"])==FANOUT
remaining=[x["id"] for x in roots if x["id"]!="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"]
assert len(roots)==6 and len(remaining)==5

cand=docs["candidate"]
assert cand["scheduler_effect"]["scope_repair_root_count_before"]==6
assert cand["scheduler_effect"]["scope_repair_root_count_after"]==5
assert cand["hard_nonclaims"][0]=="NO_CLAIM_EVIDENCE_TO_AUDIENCE_SYNTHESIS_001_WHOLE_INPUT_DOMAIN_IS_SCOPE_COMPLETE"
assert "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR_ROOT2_PERFORMANCE_WORK" in cand["scheduler_effect"]["preserve"]

receipt={
"schema":"PROJECT_BRAIN_SYNTHESIS_WHOLE_LEAF_TARGET_OBLIGATION_CUT_INDEPENDENT_PUBLIC_RUNNER_RECEIPT_V1",
"status":"PASS__WHOLE_SYNTHESIS_LEAF_UNIVERSALITY_NOT_REQUIRED_BY_CURRENT_FROZEN_TARGET__FIVE_SCOPE_ROOTS_REMAIN__ZERO_CREDIT",
"exact_source_blob_checks":"PASS",
"deduction":{
  "communication_target_dimension_count":6,
  "communication_target_scope_certificate":"PROVEN_STRONGER_EXACT_UNION_ALL_ADMISSIBLE_TARGET_INPUTS",
  "fanout_family_count":3,
  "fanout_exact_leaf_entailment":False,
  "countermodels":countermodels,
  "whole_leaf_scope_complete":False,
  "whole_leaf_current_terminal_obligation":False,
  "matched_synthesis_performance_open":True,
  "scope_repair_roots_before":6,
  "scope_repair_roots_after":5,
},
"hard_nonclaims":[
 "NO_WHOLE_LEAF_SCOPE_COMPLETENESS_CLAIM",
 "NO_SYNTHESIS_PERFORMANCE_CREDIT",
 "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
 "NO_LITERAL_TERMINAL_FINALITY_CLAIM"
]
}
Path("synthesis_target_obligation_cut_independent_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
