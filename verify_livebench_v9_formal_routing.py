#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
WRAPPER=ROOT/"diagnose_livebench_replay72_v9_formal_routing.py"
EXPECTED_WRAPPER="895b0c949284a9024661feace72efc9939929309"
EXPECTED_V2="dbc895a0e458e411aafd3c96e0ddc2c01e657375"
EXPECTED_COMPILER="1d83dffb7024666cc2202f88a0dca6819165f35a"
EXPECTED_V8_DIAG="bc5bfd7d791b1343cbcf4d09d8f41c6f73ed9f68"
EXPECTED_V8_CLASSIFIER="0c48d463989f8351e3b0a502a174b59ff391ffe8"
EXPECTED_BASE="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

checks={
 WRAPPER:EXPECTED_WRAPPER,
 ROOT/"canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py":EXPECTED_V2,
 ROOT/"canonical/runtime/instruction_constraint_compiler_v1.py":EXPECTED_COMPILER,
 ROOT/"diagnose_livebench_replay72_v8_structural.py":EXPECTED_V8_DIAG,
 ROOT/"livebench_v8_structural_classifier.py":EXPECTED_V8_CLASSIFIER,
 ROOT/"execute_livebench_if_replay72_v4_candidate.py":EXPECTED_BASE,
}
for p,w in checks.items():
    if not p.is_file() or blob(p)!=w:
        raise SystemExit("FAIL_CLOSED:BLOB_MISMATCH:"+str(p))
text=WRAPPER.read_text(encoding="utf-8")
ast.parse(text)
if "root2_livebench_if_astra_inference_adapter_v2 as adapter" not in text:
    raise SystemExit("FAIL_CLOSED:V2_IMPORT_SUBSTITUTION_MISSING")
if 'EPOCH_DIGEST="5bc110694f940f04014542c9660b98983fc178ae8489fee6db4e1e3b822c9c05"' not in text:
    raise SystemExit("FAIL_CLOSED:EPOCH_DIGEST_MISMATCH")
for forbidden in ("download_dataset(","parse_population(","REPLAY_LIMIT=200","case_73"):
    if forbidden in text:
        raise SystemExit("FAIL_CLOSED:WRAPPER_SCOPE_EXPANSION:"+forbidden)
print("PASS:LIVEBENCH_V9_FORMAL_ROUTING_WRAPPER_ZERO_CASE_VERIFICATION")
