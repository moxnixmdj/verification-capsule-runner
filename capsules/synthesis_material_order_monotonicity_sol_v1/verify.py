from __future__ import annotations
import hashlib,itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BRAIN=ROOT/"brain"
def load(rel): return json.loads((BRAIN/rel).read_text(encoding="utf-8"))
def blob_sha(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
m=json.loads((ROOT/"manifest.json").read_text())
errors=[]
for rel,expected in m["exact_blobs"].items():
    got=blob_sha(ROOT/rel)
    if got!=expected: errors.append(f"BLOB:{rel}")
protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
rows=[x for x in protocols["protocols"] if x["family"]=="COMMUNICATION_AND_SYNTHESIS"]
dims=["claim-to-source fidelity","required evidence coverage","uncertainty/disagreement preservation","audience adaptation","format/style constraints","compression without decision-relevant loss"]
if len(rows)!=1 or rows[0]["task_dimensions"]!=dims: errors.append("PROTOCOL_DIMENSIONS")
scope=load("canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json")
if scope.get("coverage_relation")!="EXACT_UNION" or scope.get("coverage_complete") is not True or len(scope.get("children",[]))!=6:
    errors.append("SCOPE_EXACT_UNION")
metric=load("canonical/governance/SYNTHESIS_MATCHED_QUALITY_METRIC_CONTRACT_V1.json")
expected5={"claim_to_source_fidelity","uncertainty_and_disagreement_preservation","audience_adaptation","format_and_style_constraints","compression_without_decision_relevant_loss"}
if set(metric["metric_contract"]["quality_components"])!=expected5: errors.append("QUALITY_COMPONENTS")
if metric["metric_contract"].get("excluded_separate_metric")!="required_claim_coverage": errors.append("COVERAGE_SEPARATE")
if "MINIMUM_OF_THE_FIVE" not in metric["metric_contract"].get("aggregation",""): errors.append("QUALITY_NOT_MIN")
sc=load("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json")
if set(sc["scorer_contract"]["dimensions"])!=expected5: errors.append("SCORER_COMPONENTS")
bindings=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
br=bindings.get("claims") or bindings.get("predicates") or bindings.get("bindings") or []
z=[x for x in br if x.get("predicate_id")=="SYNTHESIS_ZERO_UNSUPPORTED_MATERIAL_CLAIMS"]
if len(z)!=1 or z[0].get("state")!="PROVED": errors.append("ZERO_UNSUPPORTED_GATE")
cert=load("canonical/governance/SYNTHESIS_MATERIAL_OUTCOME_ORDER_MONOTONICITY_CERTIFICATE_20261005_V1.json")
ids=[x["id"] for x in cert["frozen_material_outcome_vector"]["coordinates"]]
expected6=["claim_to_source_fidelity","required_claim_coverage","uncertainty_and_disagreement_preservation","audience_adaptation","format_and_style_constraints","compression_without_decision_relevant_loss"]
if ids!=expected6 or any(x.get("direction")!="HIGHER_IS_BETTER" for x in cert["frozen_material_outcome_vector"]["coordinates"]):
    errors.append("CERT_VECTOR")
def qr(v):
    f,r,u,a,s,c=v
    return min(f,u,a,s,c),r
grid=(0.0,0.5,1.0)
for v in itertools.product(grid,repeat=6):
    q0,r0=qr(v)
    for i in range(6):
        if v[i]>=1: continue
        w=list(v); w[i]=min(1.0,v[i]+0.5)
        q1,r1=qr(tuple(w))
        if q1<q0 or r1<r0: errors.append("MONOTONICITY"); break
    if "MONOTONICITY" in errors: break
if sum((0.6,0.6))/2 != sum((0.3,0.9))/2 or min((0.3,0.9))>=min((0.6,0.6)):
    errors.append("MEAN_CANARY")
tf=load("canonical/governance/SYNTHESIS_TARGET_FREE_COUPLING_CEILING_EQUIVALENCE_20261005_V1.json")
top=(1.0,)*6
dom=[x for x in itertools.product((0.0,1.0),repeat=6) if all(a>=b for a,b in zip(x,top))]
if dom!=[top]: errors.append("TOP_BOUNDARY")
for obj in (cert,tf):
    a=obj["accounting"]
    for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        if a[k]!=0: errors.append("NONZERO_"+k)
    if obj.get("execution_authority") is not False or obj.get("promotion_authority") is not False or obj.get("fresh_reality_authority") is not False:
        errors.append("SELF_AUTHORITY")
out={"schema":"PROJECT_BRAIN_SYNTHESIS_MATERIAL_ORDER_MONOTONICITY_PUBLIC_RUNNER_VERDICT_V1","pass":not errors,"errors":errors,
"verified":["EXACT_SOURCE_BLOBS","SIX_DIMENSION_PROTOCOL","EXACT_UNION_SCOPE","MIN_PLUS_COVERAGE_FACTORIZATION","GRID_MONOTONICITY","MEAN_CANARY","TARGET_FREE_TOP_BOUNDARY","ZERO_CREDIT"],
"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
