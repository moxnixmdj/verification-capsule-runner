#!/usr/bin/env bash
set -euo pipefail
python -m canonical.tests.test_matched_scope_abductive_residual_execution_v2
python -m canonical.runtime.matched_scope_abductive_residual_execution_v2
