#!/usr/bin/env bash
set -euo pipefail
cd capsules/terminal_one_shot_attack_v1
test "$(git hash-object canonical/runtime/terminal_autopilot_v1.py)" = "3ebdcdac161d818f88d2a864f9cfce061190f846"
test "$(git hash-object canonical/tests/test_terminal_autopilot_v1.py)" = "94dd8ce92561cc15061c20891beab6df281a23da"
python -m unittest -v canonical.tests.test_terminal_autopilot_v1
