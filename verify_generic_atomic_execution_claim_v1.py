import json, math
from pathlib import Path
from canonical.runtime import h100_verified_capability_registry_v3 as r

ROOT=Path(__file__).resolve().parent
PRE=json.loads((ROOT/"canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json").read_text())
XS=[float(x) for x in PRE["x_population"]["training_x"]]

def rows(fn):
    return [{"x":x,"y":float(fn(x))} for x in XS]

snap=r.registry_snapshot()
assert snap["entry_count"]==12
assert snap["persistent_learned_bytes"]==0

checks=[
    (lambda x:-1.1+0.3*x-0.02*x**5,"CAP_AFFINE_POWER5_V1"),
    (lambda x:0.8-0.1*x-0.6*max(0.0,x+0.8),"CAP_AFFINE_HINGE_V1"),
    (lambda x:-0.2-0.03*x+0.9*math.exp(-1.3*x*x),"CAP_AFFINE_GAUSSIAN_V1"),
    (lambda x:-0.5+0.15*x-0.7*math.tanh(1.6*x),"CAP_AFFINE_TANH_V1"),
]
for fn,cid in checks:
    out=r.resolve_verified_capability(rows(fn),target="y",input_name="x")
    assert out["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE",out
    assert out["match"]["capability_id"]==cid,out
    assert out["raw_synthesis_attempts_before_hit"]==0,out

cubic=r.resolve_verified_capability(
    rows(lambda x:-0.7+0.31*x+0.42*x**3),target="y",input_name="x"
)
assert cubic["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE",cubic
assert cubic["match"]["capability_id"]=="CAP_AFFINE_CUBIC_V1",cubic

rational=r.resolve_verified_capability(
    rows(lambda x:0.2+0.1*x+0.7/(1.0+x*x)),target="y",input_name="x"
)
assert rational["status"]=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",rational

print("PASS H100_REGISTRY_V3_MULTI_FAMILY_RATCHET")
