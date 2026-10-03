#!/usr/bin/env bash
set -euo pipefail
python -m canonical.tests.test_tool_discovery_scope_interpretation_repair_v2
python -m canonical.runtime.tool_discovery_scope_interpretation_repair_v2
