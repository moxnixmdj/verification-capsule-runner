import math
from canonical.runtime import h100_verified_capability_registry_v5 as r

XS=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
def rows(fn):
    return [{"x":float(x),"y":float(fn(x))} for x in XS]

snap=r.registry_snapshot()
assert snap["entry_count"]==14
assert snap["persistent_learned_bytes"]==0

erf=r.resolve_verified_capability(
    rows(lambda x:-0.4+0.25*x-0.7*math.erf(1.6*x)),target="y",input_name="x"
)
assert erf["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE",erf
assert erf["match"]["capability_id"]=="CAP_AFFINE_ERF_V1",erf
assert erf["raw_synthesis_attempts_before_hit"]==0,erf

rational=r.resolve_verified_capability(
    rows(lambda x:-0.4+0.25*x-1.1/(1.0+x*x)),target="y",input_name="x"
)
assert rational["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE",rational
assert rational["match"]["capability_id"]=="CAP_AFFINE_RATIONAL_SAT_SQUARE_V1",rational

cosh=r.resolve_verified_capability(
    rows(lambda x:0.3+0.2*x+0.5*math.cosh(0.7*x)),target="y",input_name="x"
)
assert cosh["status"]=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",cosh

print("PASS H100_REGISTRY_V5_JIT_PRIMITIVE_RATCHET")
