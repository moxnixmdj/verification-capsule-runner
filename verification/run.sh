# Isolated P1 verifier entrypoint; deterministic spent fixtures only.
#!/usr/bin/env bash
set -euo pipefail
# PIN_EXACT_P1_REPAIR
test "$(git hash-object canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json)" = "6a4b606a759d5479bb5ddbdf29426b1a1808b007"
test "$(git hash-object canonical/runtime/p1_shared_failure_semantics_batch_preflight_v1.py)" = "1ceb5c8fda98bfe0a3f5e20288becea3ada5e5d3"
test "$(git hash-object canonical/runtime/p1_shared_failure_semantics_batch_v1.py)" = "695cfe3f283723a52bafb6299236a2d0378dc79e"
test "$(git hash-object canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py)" = "b6ba06fc6a35fa132eb19389ee256e74a63a4849"
test "$(git hash-object canonical/tests/test_p1_shared_failure_semantics_batch_v1.py)" = "7512a920c72d7bdeb2b072788e4c4bc8d2ff2d08"
python -m unittest -v canonical.tests.test_p1_shared_failure_semantics_batch_preflight_v1
python -m canonical.runtime.p1_shared_failure_semantics_batch_preflight_v1
python -m unittest -v canonical.tests.test_p1_shared_failure_semantics_batch_v1
python - <<'PY'
import json
from pathlib import Path
d=json.loads(Path("canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json").read_text())
assert d["new_reality_units_consumed"] == 0
assert d["execution_authority"] is False
assert d["promotion_authority"] is False
assert d["terminal_results_replayed"] == 0
assert d["incremental_spend_usd"] == 0
print("ZERO_FRESH_REALITY_PREFLIGHT_CONFIRMED")
PY
