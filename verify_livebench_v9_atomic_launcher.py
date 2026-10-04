#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
LAUNCHER=ROOT/"launch_livebench_v9_formal_routing_atomic.py"
DIAGNOSTIC=ROOT/"diagnose_livebench_replay72_v9_formal_routing.py"
EXPECTED_LAUNCHER_BLOB="1c303cafbf01a5c4fb98b59af2f7008de3398489"
EXPECTED_DIAGNOSTIC_BLOB="895b0c949284a9024661feace72efc9939929309"
EXPECTED_EPOCH="5bc110694f940f04014542c9660b98983fc178ae8489fee6db4e1e3b822c9c05"
EXPECTED_REF="refs/heads/livebench-v9-claims/"+EXPECTED_EPOCH

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def require(cond,msg):
    if not cond: raise AssertionError(msg)

require(blob(LAUNCHER)==EXPECTED_LAUNCHER_BLOB,"LAUNCHER_BLOB_MISMATCH")
require(blob(DIAGNOSTIC)==EXPECTED_DIAGNOSTIC_BLOB,"DIAGNOSTIC_BLOB_MISMATCH")
text=LAUNCHER.read_text(encoding="utf-8")
ast.parse(text)
require(f'EPOCH_DIGEST="{EXPECTED_EPOCH}"' in text,"EPOCH_DIGEST_MISMATCH")
require('CLAIM_REF="refs/heads/livebench-v9-claims/"+EPOCH_DIGEST' in text,"CLAIM_REF_DERIVATION")
require('method="POST"' in text,"ATOMIC_CREATE_NOT_POST")
require('if e.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")' in text,"DUPLICATE_NOT_FAIL_CLOSED")
require('if status!=201: fail("ATOMIC_ONE_USE_CLAIM_NOT_201")' in text,"NON201_NOT_FAIL_CLOSED")
require('if body.get("ref")!=CLAIM_REF: fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_REF_MISMATCH")' in text,"RESPONSE_REF_NOT_CHECKED")
require('activation_blob=os.environ.get("LIVEBENCH_V9_ACTIVATION_BLOB","")' in text,"ACTIVATION_NOT_BOUND")
i_claim=text.index("atomic_claim()")
i_import=text.index("import diagnose_livebench_replay72_v9_formal_routing as diagnostic")
i_run=text.index("diagnostic.main(authorized=True,activation_blob=activation_blob)")
require(i_claim < i_import < i_run,"LAUNCH_ORDER_INVALID")
for forbidden in ("download_dataset","parse_population","question_id","test.parquet","huggingface.co/datasets"):
    require(forbidden not in text,"LAUNCHER_TERMINAL_DATA_ACCESS:"+forbidden)
print("PASS:LIVEBENCH_V9_ATOMIC_LAUNCHER_EXACT_ZERO_CASE_VERIFICATION")
