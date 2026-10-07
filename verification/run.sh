#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/capsule"
python -m py_compile   canonical/runtime/capability_planner.py   canonical/runtime/effect_broker_receipt_resolver_v2.py   canonical/runtime/universal_verified_adaptive_solver_v1.py   canonical/runtime/universal_verified_adaptive_solver_v2.py   canonical/runtime/universal_verified_adaptive_solver_v3.py   verify_independent.py
python verify_independent.py
test -s ../result.json
