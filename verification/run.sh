#!/usr/bin/env bash
set -euo pipefail
python -m pip install --disable-pip-version-check --quiet pyarrow==19.0.1 langdetect==1.0.9 immutabledict==4.2.1 nltk==3.9.1
python verification/verify_livebench_literal_generator_grammar.py
