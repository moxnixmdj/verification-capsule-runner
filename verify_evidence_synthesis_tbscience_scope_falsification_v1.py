from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"evidence_synthesis_tbscience_scope_falsification"
CAND=SUBJECT/"candidate.json"
REG=SUBJECT/"BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
PART=SUBJECT/"FIVE_PUBLIC_BAR_FAMILY_SCOPE_PARTITION_V1.json"
P3=SUBJECT/"P3_INFORMATION_SAFE_V3_PREFLIGHT_VERIFICATION_20261002_V1.json"
TB=SUBJECT/"tb_science_task_proposal.md"

EXPECTED={
 CAND:"7ffddbee553170a019667a28d7d49b18c876f1bc",
 REG:"ee187f611a0e82b2de495ee377682f39bc31dd31",
 PART:"8f74ca3d9609737913714844a793b8566028a0aa",
 P3:"c0812ad6e7ee1e1c93d7419ed72f4fc7c9980381",
 TB:"f226e0fd7f3b6b5147dbeb627d3272921b337292",
}

def blob(p:Path)->str:
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\\0"+b).hexdigest()

def fail(x:str):
 raise SystemExit("VERIFY_FAIL:"+x)

for p,h in EXPECTED.items():
 g=blob(p)
 if g!=h: fail(f"BLOB:{p.name}:{g}:{h}")

cand=json.loads(CAND.read_text())
reg=json.loads(REG.read_text())
part=json.loads(PART.read_text())
p3=json.loads(P3.read_text())
tb=TB.read_text()

if cand.get("schema")!="PROJECT_BRAIN_EVIDENCE_AUDIENCE_SYNTHESIS_SCOPE_EQUIVALENCE_FALSIFICATION_20261005_V1": fail("SCHEMA")
if cand.get("tb_science_falsification",{}).get("result")!="FALSE": fail("RESULT_NOT_FALSE")
if cand.get("scope_reduction",{}).get("this_candidate_does_not_discharge_the_leaf") is not True: fail("LEAF_OVERCLAIM")
if cand.get("independent_verification_required") is not True: fail("INDEPENDENCE_NOT_REQUIRED")
for k in ("scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"):
 if cand.get(k) is not False: fail("AUTHORITY_NONZERO:"+k)
for k,v in cand.get("accounting",{}).items():
 if k.endswith("_delta") and v!=0: fail("CREDIT_NONZERO:"+k)
if cand.get("accounting",{}).get("incremental_spend_usd")!=0: fail("SPEND_NONZERO")
if cand.get("accounting",{}).get("terminal_cases_consumed")!=0: fail("TERMINAL_CASES_NONZERO")

leaf=None
for x in reg.get("active_contracted_residuals",[]):
 if x.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
  leaf=x; break
if not leaf: fail("LEAF_MISSING")
if leaf.get("scope")!="Grounded evidence synthesis under audience and format constraints": fail("LEAF_SCOPE_CHANGED")
if "Verified evidence units with provenance" not in leaf.get("inputs",""): fail("LEAF_INPUTS_CHANGED")
if "material uncertainty/disagreement is preserved" not in leaf.get("required_output_or_action",""): fail("LEAF_OUTPUT_CHANGED")

hg={x.get("leaf"):x.get("fanout") for x in part.get("deduplicated_surviving_leaf_hypergraph",[])}
expected_fanout=[
 "PROFESSIONAL_KNOWLEDGE_WORK",
 "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
 "AGENTIC_SCIENTIFIC_RESEARCH",
]
if hg.get("EVIDENCE_TO_AUDIENCE_SYNTHESIS_001")!=expected_fanout: fail("FANOUT_MISMATCH")

required_tb=[
 'Reject tasks that there is no way to verify the task has been solved or where grading is subjective (e.g., "summarize the existing literature on this scientific topic").',
 "We are not looking for open-ended tasks like hypothesis generation or literature review.",
 "The task must have concrete, checkable outputs",
]
for s in required_tb:
 if s not in tb: fail("TB_SCOPE_TEXT_MISSING:"+s[:40])

if "WHOLE_OPEN_ENDED_CONTRACT_SCOPE_EQUIVALENCE" not in p3.get("does_not_prove",[]): fail("P3_WHOLE_SCOPE_DISCLAIMER_MISSING")

w=cand.get("tb_science_falsification",{}).get("constructive_counterexample_class",{})
for key in ("input","required_behavior","leaf_membership","tb_science_membership","witness_consequence"):
 if not w.get(key): fail("WITNESS_FIELD_MISSING:"+key)
if not str(w.get("leaf_membership")).startswith("YES__"): fail("WITNESS_NOT_IN_LEAF")
if not str(w.get("tb_science_membership")).startswith("NO__"): fail("WITNESS_NOT_EXCLUDED")
if "EXISTS_LEAF_INPUT_NOT_IN_TB_SCIENCE_SCOPE" not in str(w.get("witness_consequence")): fail("SET_COUNTEREXAMPLE_NOT_EXPLICIT")

delete=set(cand.get("scheduler_effect",{}).get("delete",[]))
activate=set(cand.get("scheduler_effect",{}).get("activate",[]))
if "AGENTIC_SCIENTIFIC_RESEARCH__TRY_TB_SCIENCE_WHOLE_LEAF_EQUIVALENCE_FOR_EVIDENCE_TO_AUDIENCE_SYNTHESIS_001" not in delete: fail("FUTILE_BRANCH_NOT_DELETED")
if "SHARED_DIRECT_SCOPE_COMPLETE_PROOF__EVIDENCE_TO_AUDIENCE_SYNTHESIS_001" not in activate: fail("SHARED_PROOF_NOT_ACTIVATED")

print(json.dumps({
 "schema":"PROJECT_BRAIN_EVIDENCE_AUDIENCE_SYNTHESIS_TBSCIENCE_SCOPE_FALSIFICATION_INDEPENDENT_VERIFICATION_V1",
 "pass":True,
 "proof_kind":"CONTENT_BOUND_CONSTRUCTIVE_SCOPE_COUNTEREXAMPLE",
 "verified_subject_blobs":{p.name:h for p,h in EXPECTED.items()},
 "falsified_claim":"TB_SCIENCE_SCOPE_SUPERSET_OR_EQUIVALENT_TO_EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
 "witness_exists":True,
 "shared_leaf_fanout":3,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "new_reality_units_consumed":0,
 "terminal_cases_consumed":0,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False
},sort_keys=True))
