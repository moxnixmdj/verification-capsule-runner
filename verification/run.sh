#!/usr/bin/env bash
set -euo pipefail
python -m unittest -v canonical.tests.test_current_terminal_information_dominance_v1
python -m canonical.runtime.current_terminal_information_dominance_v1
