from __future__ import annotations
import ast, hashlib, json
from pathlib import Path
R=Path(__file__).resolve().parent/"subject"/"synthesis_scope_overextension"
FILES={
 "q":(R/"SYNTHESIS_SCOPE_CERTIFICATE_REUSE_OVEREXTENSION_QUARANTINE_20261005_V1.json","c1b2d488dfd38c27b533f98424036be874d5e829"),
 "a":(R/"EVIDENCE_SYNTHESIS_EXISTING_SCOPE_CERTIFICATE_REUSE_ACTIVATION_20261005_V1.json","71c7dfbd8154319fe3f3d71ab1d99f2d6530b2f4"),
 "c":(R/"SYNTHESIS_SCOPE_CERTIFICATE_V1.json","dea9028f92f111ee3c8be71615fa4b02e8a8bfb6"),
 "d":(R/"SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_V1.json","72f31ed22331be258e8762bedf0f0df3596af8d7"),
 "v":(R/"synthesis_lossless_scope_decomposition_verifier_v1.py","5ba044bc63cc6d47a4034b166e8f8e099f601c66"),
 "s":(R/"SYNTHESIS_P3_CONTRACT_SEMANTIC_REDUCTION_20261005_V1.json","f6b83872bf1288693e4e5250a561599f1cc6fa75")
}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def fail(x): raise SystemExit("VERIFY_FAIL:"+x)
for k,(p,h) in FILES.items():
 if blob(p)!=h: fail("BLOB:"+k+":"+blob(p)+":"+h)
q=json.loads(FILES["q"][0].read_text())
a=json.loads(FILES["a"][0].read_text())
c=json.loads(FILES["c"][0].read_text())
d=json.loads(FILES["d"][0].read_text())
s=json.loads(FILES["s"][0].read_text())
src=FILES["v"][0].read_text()
ast.parse(src)

if q.get("scheduling_authority") is not False: fail("QUARANTINE_SELF_ACTIVATED")
if q.get("independent_verification_required") is not True: fail("NO_INDEPENDENT_GATE")
if a.get("scheduling_authority") is not True: fail("SUBJECT_OVEREXTENSION_NOT_ACTIVE")
if c.get("target_scope_id")!="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR": fail("CERT_TARGET")
if c.get("witness_scope_id")!="scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL": fail("CERT_WITNESS")
hard=set(d.get("hard_rules") or [])
if "THIS_CERTIFICATE_PROVES_ONLY_TARGET_SCOPE_SUBSET_OF_THE_EXISTING_VERIFIED_SYNTHESIS_WITNESS_SCOPE" not in hard:
 fail("NARROW_SCOPE_RULE_MISSING")
if s.get("remaining_single_root",{}).get("id")!="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS":
 fail("TYPED_DOMAIN_RESIDUAL_MISSING")
if "NO_SCOPE_COMPLETENESS_CLAIM" not in set(s.get("hard_nonclaims") or []):
 fail("SEMANTIC_REDUCTION_SCOPE_NONCLAIM_MISSING")

# The independent decomposition verifier proves dimension-set/contract-fragment coverage.
required_checks=[
 "TARGET_DIMENSION_SET_DRIFT","CANDIDATE_DIMENSION_SET_DRIFT","CONTRACT_FRAGMENT_MISMATCH",
 "TARGET_ATOM_DIMENSIONS_DRIFT","WITNESS_DIMENSION_ATOMS_NOT_PROVED"
]
for token in required_checks:
 if token not in src: fail("VERIFIER_EXPECTED_CHECK_MISSING:"+token)

# It contains no evaluator over a normalized synthesis input universe. In particular the
# only loops in evaluate are over expected source blobs and dimension bindings/witnesses,
# and there is no case/input generator, normalized-input quantifier, or totality function.
tree=ast.parse(src)
func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="evaluate")
names={n.id for n in ast.walk(func) if isinstance(n,ast.Name)}
calls=[]
for n in ast.walk(func):
 if isinstance(n,ast.Call):
  if isinstance(n.func,ast.Name): calls.append(n.func.id)
  elif isinstance(n.func,ast.Attribute): calls.append(n.func.attr)
for forbidden in ("generate_case","public_task","normalize_input","enumerate_inputs","prove_totality","all_admissible_inputs"):
 if forbidden in names or forbidden in calls or forbidden in src:
  fail("UNEXPECTED_INPUT_DOMAIN_PROOF_MECHANISM:"+forbidden)

# Logical countermodel: A⊆B never entails B is complete over universe U.
# Construct finite sets satisfying A⊆B while leaving an admissible element outside B.
U={"bound_input","unbound_admissible_input"}
A={"bound_input"}
B={"bound_input"}
if not A.issubset(B): fail("COUNTERMODEL_PREMISE")
if B==U: fail("COUNTERMODEL_NOT_OPEN")
# This is exactly the invalid direction used by the whole-leaf reuse: proven target subset
# of witness cannot certify witness==all admissible behavioral inputs.
if q.get("invalid_inference",{}).get("verdict")!="NOT_PROVED": fail("QUARANTINE_VERDICT")
if q.get("correct_remaining_scope_root",{}).get("fanout_count")!=3: fail("FANOUT")
for k,val in q.get("accounting",{}).items():
 if k.endswith("_delta") and val!=0: fail("NONZERO_CREDIT:"+k)
print(json.dumps({
 "schema":"PROJECT_BRAIN_SYNTHESIS_SCOPE_OVEREXTENSION_INDEPENDENT_VERIFICATION_V1",
 "pass":True,
 "proof_kind":"CONTENT_BOUND_LOGICAL_COUNTERMODEL_PLUS_VERIFIER_SEMANTIC_BOUNDARY",
 "preserved_predicate_scope_certificate":True,
 "whole_leaf_input_domain_completeness_proved":False,
 "remaining_root":"SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS",
 "fanout":3,
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
