#!/usr/bin/env bash
set -euo pipefail
python canonical/tests/test_matched_scope_abductive_residual_execution_v2.py
python -m canonical.runtime.matched_scope_abductive_residual_execution_v2
