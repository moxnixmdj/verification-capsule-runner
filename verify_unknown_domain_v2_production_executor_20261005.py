from __future__ import annotations
import ast
import hashlib
import inspect
import json
from pathlib import Path

import execute_unknown_domain_v2_production_20261005 as prod

ROOT=Path(__file__).resolve().parent

doc, exact = prod.build_preflight_input()
pre = prod.preflight(doc)
assert pre["ready"] is True, pre
assert pre["status"] == "READY_FOR_ATOMIC_ONE_USE_CLAIM_ONLY"
assert doc["qualification_independent_pass"] is True
assert doc["predicate_local_activation_independent_pass"] is True
assert doc["production_cases_consumed"] == 0
assert doc["production_beacon_generated"] is False
assert doc["global_fresh_reality"] is False
assert doc["one_use_claim_created"] is False
assert doc["execution_started"] is False

lease = prod.execution_lease(exact)
digest, ref = prod.claim_ref_for_lease(lease)
assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
assert ref == "refs/heads/unknown-domain-direct-claims/" + digest
assert lease["production_populations_allowed"] == 1
assert lease["production_cases_allowed"] == 27
assert lease["replay_allowed"] is False
assert lease["replacement_allowed"] is False
assert lease["post_result_tuning_allowed"] is False

source = inspect.getsource(prod.execute_production)
tree = ast.parse(source)
calls=[]
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        name=""
        if isinstance(node.func, ast.Name):
            name=node.func.id
        elif isinstance(node.func, ast.Attribute):
            name=node.func.attr
        calls.append((getattr(node, "lineno", 10**9), name))
positions={}
for lineno,name in calls:
    positions.setdefault(name, lineno)
assert positions["create_atomic_claim"] < positions["generate_production_population"], positions

text = source
assert text.index("claim_status, claim_response = create_atomic_claim") < text.index("import secrets")
assert text.index("import secrets") < text.index("generator.generate_production_population")

class Stop(Exception):
    pass

seen={"claim":0}
def duplicate_claim(_ref):
    seen["claim"] += 1
    return 422, {"message":"Reference already exists"}

orig = prod.create_atomic_claim
prod.create_atomic_claim = duplicate_claim
try:
    result = prod.execute_production()
finally:
    prod.create_atomic_claim = orig

assert seen["claim"] == 1
assert result["status"] == "ABORTED_BEFORE_BEACON__ATOMIC_CLAIM_NON201"
assert result["terminal_cases_consumed"] == 0
assert result["production_cases_generated"] == 0
assert "aggregate_from_frozen_scorer" not in result

if prod.RESULT_PATH.exists():
    prod.RESULT_PATH.unlink()

print(json.dumps({
    "status":"INDEPENDENT_PREPRODUCTION_EXECUTOR_VERIFICATION_PASS",
    "preflight_ready":True,
    "exact_subject_count":len(exact),
    "claim_before_fresh_entropy":True,
    "duplicate_claim_aborts_before_beacon":True,
    "terminal_cases_consumed":0,
}, sort_keys=True))
