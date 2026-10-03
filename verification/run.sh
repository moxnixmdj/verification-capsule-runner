#!/usr/bin/env bash
set -euo pipefail

test "$(git hash-object canonical/runtime/acceptance_backprop_compiler_v1.py)" = "b63c18a5a66eeb978780d2560f0f741ad255ad68"
test "$(git hash-object canonical/tests/test_acceptance_backprop_compiler_v1.py)" = "3f9b121aec301c549a4a872f73d51f0e919901bc"
test "$(git hash-object canonical/governance/ACCEPTANCE_BACKPROP_COMPILER_V1.json)" = "3066c7be791d949994bacbf76cfbc50a470539da"

python -m py_compile canonical/runtime/acceptance_backprop_compiler_v1.py
python -m py_compile canonical/tests/test_acceptance_backprop_compiler_v1.py
PYTHONPATH=. python -m unittest -v canonical.tests.test_acceptance_backprop_compiler_v1

PYTHONPATH=. python - <<'PY'
from canonical.runtime.acceptance_backprop_compiler_v1 import (
    SCHEMA,
    evaluate,
    population_commitment_sha256,
)

ids=[f"c{i:03d}" for i in range(600)]
payload={
    "schema":SCHEMA,
    "metric_semantics_frozen":True,
    "population_frozen":True,
    "scorer_identity_bound":True,
    "metric_type":"BINARY_RATE",
    "population_ids":ids,
    "population_commitment_sha256":population_commitment_sha256(ids),
    "threshold_percent":40,
    "partitions":[],
}
v=evaluate(payload)
assert v["pass"] is True,v
assert v["decision"]=="UNRESOLVED",v
assert v["threshold_success_count"]==240,v
assert v["minimum_additional_success_mass_required"]==240,v
assert v["new_reality_units_consumed"]==0,v
assert v["capability_credit_delta"]==0 and v["family_credit_delta"]==0 and v["terminal_credit_delta"]==0,v
assert v["execution_authority"] is False and v["promotion_authority"] is False,v
print("ACCEPTANCE_BACKPROP_V1_EXACT_ZERO_CREDIT_PASS")
PY
