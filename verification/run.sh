# Isolated P1 verifier entrypoint; deterministic spent fixtures only.
#!/usr/bin/env bash
set -euo pipefail
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
