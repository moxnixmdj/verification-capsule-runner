from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "runtime.py":"afed2f90c85255feaa78d441d12c230985ca102d",
 "brain_tests.py":"83f12369870fed9b54937bc9afc8976c0ff0a0a4",
 "activation.json":"18150634f3984ad26f47b1b49b260a78db9e06db",
 "frontier.json":"4b5517dbd12978f8ffe481fb775e85592c7790c8",
 "adjudication.json":"9f2831b5daf0bf811a11c322d85906869fdef433",
}
def blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,e in EXPECTED.items():
    g=blob_sha(ROOT/n)
    assert g==e,(n,g,e)

spec=importlib.util.spec_from_file_location("pruner",ROOT/"runtime.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

frontier=json.loads((ROOT/"frontier.json").read_text())
adj=json.loads((ROOT/"adjudication.json").read_text())
activation=json.loads((ROOT/"activation.json").read_text())
out=m.prune(frontier,[adj])
assert out["status"].startswith("PASS")
assert out["falsified_atom_count"]==1
assert out["blocked_certificate_ids"]==["TB4_ATTAINABLE_ROUTE_CERTIFICATE"]
assert out["uncovered_target_predicates"]==["CODING_TB4_GE_66_4"]
assert out["alternative_certificate_required"]==["CODING_TB4_GE_66_4"]
assert out["target_predicates_removed"]==[]
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert activation["expected_live_projection"]["blocked_certificate_ids"]==out["blocked_certificate_ids"]
assert activation["expected_live_projection"]["uncovered_target_predicates"]==out["uncovered_target_predicates"]

# Adversarial: a false atom cannot erase a target when another certificate still covers it.
f={"unresolved_predicates":["T"],"certificates":[
 {"id":"A","target_predicates":["T"],"requires":["P"]},
 {"id":"B","target_predicates":["T"],"requires":["Q"]},
]}
a={"status":"INDEPENDENT_PUBLIC_RUNNER_PASS__TEST","atom":{
 "proposition":"P","parent_certificate_id":"A","target_predicate":"T",
 "adjudication":"FALSIFIED_UNDER_CURRENT_FROZEN_NO_REPLAY_ROUTE"}}
x=m.prune(f,[a])
assert x["uncovered_target_predicates"]==[]
assert x["blocked_targets_still_covered_by_alternative_certificate"]==["T"]

# Adversarial: wrong literal and non-independent receipt fail closed.
a_bad=json.loads(json.dumps(a)); a_bad["atom"]["proposition"]="NOT_P"
assert m.prune(f,[a_bad])["status"]=="FAIL_CLOSED"
a_bad=json.loads(json.dumps(a)); a_bad["status"]="CANDIDATE"
assert m.prune(f,[a_bad])["status"]=="FAIL_CLOSED"

print(json.dumps({
 "schema":"PROJECT_BRAIN_PROOF_ATOM_ROUTE_PRUNER_PUBLIC_RUNNER_VERIFICATION_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__TB4_FALSE_ATOM_PRUNES_ONLY_ROUTE__TARGET_PRESERVED__ALTERNATIVE_CERTIFICATE_REQUIRED__ZERO_CREDIT",
 "exact_brain_blobs":EXPECTED,
 "live_projection":out,
 "new_reality_units_consumed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
