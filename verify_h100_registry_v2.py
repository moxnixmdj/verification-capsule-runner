import math
from canonical.runtime import h100_verified_capability_registry_v2 as r

def rows(fn):
    xs=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
    return [{"x":float(x),"y":float(fn(x))} for x in xs]

snap=r.registry_snapshot()
assert snap["entry_count"]==8, snap
assert snap["entries"][-1]["capability_id"]=="CAP_AFFINE_CUBIC_V1", snap
assert snap["persistent_learned_bytes"]==0

cubic=r.resolve_verified_capability(rows(lambda x:-0.7+0.31*x+0.42*x**3),target="y",input_name="x")
assert cubic["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE", cubic
assert cubic["match"]["capability_id"]=="CAP_AFFINE_CUBIC_V1", cubic
assert cubic["raw_synthesis_attempts_before_hit"]==0, cubic
want=-0.7+0.31*1.7+0.42*1.7**3
assert abs(r.predict(cubic,{"x":1.7})-want)<1e-9

sinusoid=r.resolve_verified_capability(rows(lambda x:0.4+0.15*x+1.3*math.sin(1.73*x+0.4)),target="y",input_name="x")
assert sinusoid["status"]=="LIBRARY_HIT__VERIFY_BEFORE_USE", sinusoid
assert sinusoid["match"]["capability_id"]=="CAP_LINEAR_TREND_SINUSOID_V1", sinusoid

quartic=r.resolve_verified_capability(rows(lambda x:0.2+0.1*x+0.7*x**4),target="y",input_name="x")
assert quartic["status"]=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED", quartic

print("PASS registry_v2 cubic_hit legacy_hit quartic_miss zero_learned")
