#!/usr/bin/env python3
from __future__ import annotations
import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "unittest", "-v",
    "canonical.tests.test_residual_witness_retrieval_compiler_v1",
    "canonical.tests.test_open_research_query_focus_relevance",
], check=True)
print("CURRENT_RESIDUAL_WITNESS_RETRIEVAL_VERIFIED")
