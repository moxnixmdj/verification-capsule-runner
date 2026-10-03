from __future__ import annotations
from canonical.runtime.tool_discovery_proof_router_v2 import route, _sha, PARTITION_SCHEMA

POL={"independent_verified":True,"exact_byte_bound":True,"program_soundness_verified":True,"policy_version":"V8"}
IDS={"independent_verified":True,"identity_scope_complete":True,"scope_relation":"EXACT","common_brain_opus_authority":True}

def receipt(p):
    return {"independent_verified":True,"partition_version":"V2","minimum_reality_partition_verified":True,"partition_result_sha256":_sha(p)}

def base(**kw):
    d={"schema":PARTITION_SCHEMA,"identity_scope_complete":True,"recommended_safe_probe":None,"irreducible_routes":[]}
    d.update(kw)
    return d

def call(p,pol=POL,ids=IDS,r=None):
    return route(policy_receipt=pol,identity_scope_receipt=ids,partition_result=p,partition_receipt=r or receipt(p))

u=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
o=call(u)
assert o["status"]=="UNIVERSAL_REGION__FORMAL_PROGRAM_PROOF_ONLY"
assert o["matched_comparator_allowed_now"] is False and o["execution_authority"] is False

s=base(status="SAFE_PROGRESS_REQUIRED__PROBE_BEFORE_MATCHED_EVIDENCE",minimum_reality_action="SAFE_PROBE",universal_proof_eligible=False,safe_progress_available=True,matched_comparator_required_now=False,recommended_safe_probe={"tool_id":"cheap","capability":"A"})
o=call(s)
assert o["status"]=="SAFE_OBSERVATION_REQUIRED__MATCHED_EVIDENCE_FORBIDDEN_YET"
assert o["matched_comparator_allowed_now"] is False and o["safe_observation_required_now"] is True

m=base(status="MATCHED_COMPARATOR_REQUIRED__IRREDUCIBLE_OBSERVABILITY_BOUND",minimum_reality_action="MATCHED_COMPARATOR",universal_proof_eligible=False,safe_progress_available=False,matched_comparator_required_now=True,irreducible_routes=[{"tool_id":"cheap","unsafe_unknown_capabilities":["A"]}])
o=call(m)
assert o["status"]=="MATCHED_ONLY_RESIDUAL__SAFE_OBSERVATION_CLOSED"
assert o["matched_comparator_allowed_now"] is True and o["execution_authority"] is False

for field in ("independent_verified","exact_byte_bound","program_soundness_verified"):
    p=dict(POL); p[field]=False
    assert call(u,pol=p)["status"]=="FAIL_CLOSED"
p=dict(POL); p["policy_version"]="V5"
assert "POLICY_NOT_V6_OR_SUCCESSOR" in call(u,pol=p)["failures"]

for mutate in (
    {"independent_verified":False},
    {"identity_scope_complete":False},
    {"scope_relation":"SUPERSET"},
    {"common_brain_opus_authority":False},
):
    x=dict(IDS); x.update(mutate)
    assert call(u,ids=x)["status"]=="FAIL_CLOSED"

bad=receipt(u); bad["partition_result_sha256"]="sha256:"+"0"*64
assert "PARTITION_RECEIPT_RESULT_DIGEST_MISMATCH" in call(u,r=bad)["failures"]
bad=receipt(u); bad["partition_version"]="V1"
assert "PARTITION_NOT_V2" in call(u,r=bad)["failures"]
bad=receipt(u); bad["minimum_reality_partition_verified"]=False
assert "MINIMUM_REALITY_PARTITION_NOT_VERIFIED" in call(u,r=bad)["failures"]

amb=base(status="SAFE_PROGRESS_REQUIRED__PROBE_BEFORE_MATCHED_EVIDENCE",minimum_reality_action="SAFE_PROBE",universal_proof_eligible=True,safe_progress_available=True,matched_comparator_required_now=False,recommended_safe_probe={"tool_id":"T","capability":"A"})
assert "PARTITION_NOT_EXACTLY_ONE_OF_THREE_REGIONS" in call(amb)["failures"]

fake=base(status="MATCHED_COMPARATOR_REQUIRED__IRREDUCIBLE_OBSERVABILITY_BOUND",minimum_reality_action="MATCHED_COMPARATOR",universal_proof_eligible=False,safe_progress_available=False,matched_comparator_required_now=True,irreducible_routes=[])
assert "MATCHED_REGION_WITHOUT_IRREDUCIBILITY_WITNESS" in call(fake)["failures"]

fake=base(status="MATCHED_COMPARATOR_REQUIRED__IRREDUCIBLE_OBSERVABILITY_BOUND",minimum_reality_action="MATCHED_COMPARATOR",universal_proof_eligible=False,safe_progress_available=False,matched_comparator_required_now=True,irreducible_routes=[{"tool_id":"T"}],recommended_safe_probe={"tool_id":"T","capability":"A"})
assert "MATCHED_REGION_STILL_CARRIES_SAFE_PROBE" in call(fake)["failures"]

print("INDEPENDENT_TOOL_DISCOVERY_PROOF_ROUTER_V2_PASS")
