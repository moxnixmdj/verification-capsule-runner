#!/usr/bin/env python3
import importlib.util
import json
import math
import pathlib
import subprocess
import sys

BASE=pathlib.Path("subject/synthesis_matched_quality_metric_v1_20261004_sol")
FILES={
    "scorer":BASE/"scorer.py",
    "contract":BASE/"contract.json",
    "protocol":BASE/"protocol.json",
    "normalization":BASE/"normalization.json",
    "scope":BASE/"scope.json",
    "coverage":BASE/"coverage.json",
    "prewave":BASE/"prewave.json",
}
EXPECTED={
    "scorer":"116b7394f4b0a6845056c798e966f4cc26f294bf",
    "contract":"0886f7592875a5b750cdd401aa783351ab2f0854",
    "protocol":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "normalization":"515f24f3000218d324be4a7c774b42f790a6ebaa",
    "scope":"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
    "coverage":"f2ef80facb39264b1e12b81e451eb4499a3b987f",
    "prewave":"46cce2be4e277485b7c83233630d0e2fe57d06d1",
}
def blob(path):
    return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()

for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

docs={k:json.loads(p.read_text()) for k,p in FILES.items() if k!="scorer"}
c=docs["contract"]
assert c["schema"]=="PROJECT_BRAIN_SYNTHESIS_MATCHED_QUALITY_METRIC_CONTRACT_V1"
assert c["target_predicate"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
assert c["independent_verification_required"] is True
assert c["execution_authority"] is False
assert c["promotion_authority"] is False
assert c["fresh_reality_authority"] is False
assert all(v==0 for v in c["accounting"].values())

# Exact authority hash chain.
fa=c["frozen_authority"]
assert fa["terminal_protocol"]["git_blob_sha"]==EXPECTED["protocol"]
assert fa["target_normalization"]["git_blob_sha"]==EXPECTED["normalization"]
assert fa["scope_certificate"]["git_blob_sha"]==EXPECTED["scope"]
assert fa["required_claim_coverage_ceiling"]["git_blob_sha"]==EXPECTED["coverage"]
assert fa["prewave_protocol"]["git_blob_sha"]==EXPECTED["prewave"]

# Frozen protocol really names the dimensions and independent quality metric.
protocol=docs["protocol"]
row=next(x for x in protocol["protocols"] if x["family"]=="COMMUNICATION_AND_SYNTHESIS")
assert row["proof_mode"]=="MATCHED_GROUNDED_SYNTHESIS_NONINFERIORITY"
dims=set(row["task_dimensions"])
expected_dims={
    "claim-to-source fidelity",
    "required evidence coverage",
    "uncertainty/disagreement preservation",
    "audience adaptation",
    "format/style constraints",
    "compression without decision-relevant loss",
}
assert dims==expected_dims
assert "independent_quality_score" in row["primary_metrics"]
assert "required_claim_coverage" in row["primary_metrics"]

# Target normalization separately requires quality and coverage.
norm=docs["normalization"]
target=next(x for x in norm["targets"] if x["predicate_id"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR")
assert "metric:matched_quality" in target["required_atoms"]
assert "metric:required_claim_coverage" in target["required_atoms"]
mr={x["metric"] for x in target["metric_requirements"]}
assert mr=={"matched_quality_noninferiority","required_claim_coverage_noninferiority"}

# Scope side is independently complete/stronger, but performance remains open.
scope=docs["scope"]
assert scope["verified"] is True and scope["independent"] is True
assert scope["scope_relation"]=="PROVEN_STRONGER"
assert scope["coverage_complete"] is True
assert scope["consequence"]["predicate_remains_open_for_root2"] is True

# Coverage proof explicitly does not infer matched quality.
coverage=docs["coverage"]
assert "metric:matched_quality" in coverage["explicitly_not_proved"]
assert "matched_quality_noninferiority" in coverage["explicitly_not_proved"]

# Prewave protocol requires scorer+metric freezing before exposure.
pre=docs["prewave"]
req=set(pre["surface_binding_requirements"])
assert "SCORER_OR_ORACLE_VERSION_OR_HASH" in req
assert "METRIC_AND_THRESHOLD" in req
assert pre["fresh_terminal_evidence_consumed"]==0

# Load exact candidate scorer.
spec=importlib.util.spec_from_file_location("synthesis_metric",FILES["scorer"])
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

expected_components=(
    "claim_to_source_fidelity",
    "uncertainty_and_disagreement_preservation",
    "audience_adaptation",
    "format_and_style_constraints",
    "compression_without_decision_relevant_loss",
)
assert m.QUALITY_COMPONENTS==expected_components
assert c["metric_contract"]["quality_components"]==list(expected_components)
assert c["metric_contract"]["excluded_separate_metric"]=="required_claim_coverage"
assert c["metric_contract"]["aggregation"]=="MATCHED_QUALITY_EQUALS_MINIMUM_OF_THE_FIVE_QUALITY_COMPONENT_SCORES"

def vals(v=1.0):
    return {k:v for k in expected_components}

# Ceiling and non-compensation.
assert m.aggregate(vals())["matched_quality"]==1.0
x=vals(); x["audience_adaptation"]=0.31
assert m.aggregate(x)["matched_quality"]==0.31
x=vals(); x["compression_without_decision_relevant_loss"]=0.0
assert m.aggregate(x)["matched_quality"]==0.0

# Unsupported material claims are a hard zero.
assert m.aggregate(vals(),unsupported_material_claims=1)["matched_quality"]==0.0

# Coverage cannot be injected into quality.
x=vals(); x["required_claim_coverage"]=1.0
try:
    m.aggregate(x)
    raise AssertionError("coverage injection was accepted")
except ValueError:
    pass

# Missing, nonfinite, boolean and out-of-range values fail closed.
for mut in ("missing","nan","inf","low","high","bool"):
    x=vals()
    if mut=="missing": del x["claim_to_source_fidelity"]
    elif mut=="nan": x["claim_to_source_fidelity"]=math.nan
    elif mut=="inf": x["claim_to_source_fidelity"]=math.inf
    elif mut=="low": x["claim_to_source_fidelity"]=-0.001
    elif mut=="high": x["claim_to_source_fidelity"]=1.001
    elif mut=="bool": x["claim_to_source_fidelity"]=True
    try:
        m.aggregate(x)
        raise AssertionError(mut)
    except ValueError:
        pass

# Monotonicity: lowering any component cannot improve quality.
base=m.aggregate(vals(0.8))["matched_quality"]
for k in expected_components:
    x=vals(0.8); x[k]=0.7
    assert m.aggregate(x)["matched_quality"]<=base

# Contract does not claim results it cannot have.
for forbidden in (
    "NO_MATCHED_QUALITY_RESULT",
    "NO_BRAIN_SCORE",
    "NO_OPUS_SCORE",
    "NO_MATCHED_NONINFERIORITY_RESULT",
    "NO_FRESH_REALITY_AUTHORITY",
):
    assert forbidden in c["hard_nonclaims"]

print("PASS: exact synthesis matched-quality candidate blobs and authority chain verified")
print("PASS: metric is preexposure, deterministic, monotone and non-compensatory")
print("PASS: required-claim coverage remains a separate metric")
print("PASS: invalid/missing/nonfinite/out-of-range inputs fail closed")
print("PASS: zero spend, zero cases, zero acceptance credit, no execution or fresh-reality authority")
