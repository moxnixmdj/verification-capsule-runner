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


# Adaptive terminal minimum-cut V1 independent capsule.
python verify_terminal_adaptive_minimum_cut_v1.py
python - <<'PY'
import importlib
for name in (
    "canonical.tests.test_minimum_terminal_cut_solver_v2",
    "canonical.tests.test_terminal_adaptive_supertransaction_v1",
):
    m=importlib.import_module(name)
    tests=[getattr(m,k) for k in sorted(dir(m)) if k.startswith("test_") and callable(getattr(m,k))]
    assert tests,(name,"NO_TESTS")
    for fn in tests:
        fn()
        print("PASS",name,fn.__name__)
PY
python canonical/runtime/terminal_adaptive_supertransaction_v1.py > /tmp/terminal_adaptive_result.json
python - <<'PY'
import json
x=json.load(open("/tmp/terminal_adaptive_result.json"))
assert x["pass"] is True,x
assert x["causal_phase_upper_bound"]==2,x
assert x["automatic_finality"]["separate_manual_phase_required"] is False,x
assert x["terminal_state"]["unresolved_predicates"]==26,x
assert x["fresh_reality_authority"] is False,x
print("TERMINAL_ADAPTIVE_MINIMUM_CUT_ISOLATED_PASS")
PY

# adaptive-mincut-trigger-v2: rerun after removing third-party pytest dependency.
