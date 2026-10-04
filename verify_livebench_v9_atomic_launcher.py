#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
LAUNCHER=ROOT/"launch_livebench_v9_formal_routing_atomic.py"
WRAPPER=ROOT/"diagnose_livebench_replay72_v9_formal_routing.py"
EXPECTED_LAUNCHER="7da685b89a2c1023c0c1a2c7a65d1f7972efb387"
EXPECTED_WRAPPER="895b0c949284a9024661feace72efc9939929309"
EPOCH="5bc110694f940f04014542c9660b98983fc178ae8489fee6db4e1e3b822c9c05"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

if blob(LAUNCHER)!=EXPECTED_LAUNCHER: raise SystemExit("FAIL_CLOSED:LAUNCHER_BLOB")
if blob(WRAPPER)!=EXPECTED_WRAPPER: raise SystemExit("FAIL_CLOSED:WRAPPER_BLOB")
text=LAUNCHER.read_text(encoding="utf-8")
ast.parse(text)
checks=[
 f'EPOCH_DIGEST="{EPOCH}"' in text,
 'CLAIM_REF="refs/heads/livebench-v9-claims/"+EPOCH_DIGEST' in text,
 'method="POST"' in text,
 'if e.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")' in text,
 'if status!=201: fail("ATOMIC_ONE_USE_CLAIM_NOT_201")' in text,
 'LIVEBENCH_V9_ACTIVATION_BLOB' in text,
]
if not all(checks): raise SystemExit("FAIL_CLOSED:LAUNCHER_CONTRACT")
if not text.index("atomic_claim()") < text.index("import diagnose_livebench_replay72_v9_formal_routing as diagnostic") < text.index("diagnostic.main(authorized=True,activation_blob=activation_blob)"):
    raise SystemExit("FAIL_CLOSED:ORDER")
for forbidden in ("download_dataset","parse_population","test.parquet"):
    if forbidden in text: raise SystemExit("FAIL_CLOSED:LAUNCHER_DATASET_ACCESS")
print("PASS:LIVEBENCH_V9_ATOMIC_LAUNCHER_ZERO_CASE_VERIFICATION")
