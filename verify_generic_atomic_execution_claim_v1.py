import math
from canonical.runtime import h100_verified_capability_registry_v4 as r

XS=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
def rows(fn):
    return [{"x":float(x),"y":float(fn(x))} for x in XS]

snap=r.registry_snapshot()
assert snap["entry_count"]==13
assert snap["persistent_learned_bytes"]==0

rational=r.resolve_verified_capability(
    rows(lambda x:-0.4+0.25*x-1.1/(1.0+x*x)),target="y",input_name="x"
)
assert rational["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE",rational
assert rational["match"]["capability_id"]=="CAP_AFFINE_RATIONAL_SAT_SQUARE_V1",rational
assert rational["raw_synthesis_attempts_before_hit"]==0,rational

power5=r.resolve_verified_capability(
    rows(lambda x:-1.1+0.3*x-0.02*x**5),target="y",input_name="x"
)
assert power5["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE",power5
assert power5["match"]["capability_id"]=="CAP_AFFINE_POWER5_V1",power5

unknown=r.resolve_verified_capability(
    rows(lambda x:0.2+0.1*x+0.7*math.log1p(abs(x))),target="y",input_name="x"
)
assert unknown["status"]=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",unknown

print("PASS H100_REGISTRY_V4_EXPRESSION_ESCAPE_RATCHET")
