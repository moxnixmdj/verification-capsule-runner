#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED_ACTIVATION_BLOB="27f7af154b419cc9961eb9f9882823a8dc9780ea"
EXPECTED={
  "launch_livebench_v8_structural_atomic.py":"08286046cdb87bcf206d13d520536a4564f6b47f",
  "diagnose_livebench_replay72_v8_structural.py":"bc5bfd7d791b1343cbcf4d09d8f41c6f73ed9f68",
  "livebench_v8_structural_classifier.py":"0c48d463989f8351e3b0a502a174b59ff391ffe8",
  "execute_livebench_if_replay72_v4_candidate.py":"2a57ce896ddbd6819246aab8b44d17a00f36b61e",
  "subject/livebench_v8_structural_activation.json":EXPECTED_ACTIVATION_BLOB,
}
def blob(path):
    return subprocess.check_output(["git","hash-object",str(ROOT/path)],text=True).strip()
for path,want in EXPECTED.items():
    got=blob(path)
    if got!=want:
        raise SystemExit(f"FAIL_CLOSED:BLOB_MISMATCH:{path}:{want}:{got}")
a=json.loads((ROOT/"subject/livebench_v8_structural_activation.json").read_text())
checks=[
 a.get("schema")=="PROJECT_BRAIN_LIVEBENCH_V8_STRUCTURAL_REFINEMENT_ACTIVATION_V1",
 a.get("active") is True,
 a.get("target_predicate")=="LIVEBENCH_IF_GE_65_7",
 a.get("benchmark_id")=="LIVEBENCH_IF_2026_06_25",
 a.get("scope",{}).get("replay_prefix_limit")==72,
 a.get("scope",{}).get("already_exposed_prefix_only") is True,
 a.get("scope",{}).get("new_case_exposure") is False,
 a.get("scope",{}).get("case_73_or_later") is False,
 a.get("authority",{}).get("execution") is True,
 a.get("authority",{}).get("replay_existing_prefix") is True,
 a.get("authority",{}).get("new_case_exposure") is False,
 a.get("authority",{}).get("promotion") is False,
 a.get("authority",{}).get("acceptance_credit") is False,
 a.get("exact_binding",{}).get("epoch_digest_sha256")=="78f7e799c3e1edf70516c02badebde0adbad7c5846aec8fbff53f8db2152f192",
]
if not all(checks):
    raise SystemExit("FAIL_CLOSED:ACTIVATION_SEMANTICS_MISMATCH")
print("LIVEBENCH_V8_EXECUTION_BINDING_VERIFIED")
