#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
WRAPPER=ROOT/"diagnose_livebench_replay72_v10_formal_routing.py"
LAUNCHER=ROOT/"launch_livebench_v10_formal_routing_atomic.py"
EXPECTED_WRAPPER="21965df9d6bb6bd094a89907b21516a286e60f30"
EXPECTED_LAUNCHER="632ff11579464788f94e81738d5bc7cdd3635f75"
EXPECTED_COMPILER="a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f"
EXPECTED_ADAPTER="dbc895a0e458e411aafd3c96e0ddc2c01e657375"
EXPECTED_EPOCH="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"

def blob(p):
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def require(x,msg):
    if not x: raise AssertionError(msg)

require(blob(WRAPPER)==EXPECTED_WRAPPER,"WRAPPER_BLOB_MISMATCH")
require(blob(LAUNCHER)==EXPECTED_LAUNCHER,"LAUNCHER_BLOB_MISMATCH")
require(blob(ROOT/"canonical/runtime/instruction_constraint_compiler_v1.py")==EXPECTED_COMPILER,"COMPILER_BLOB_MISMATCH")
require(blob(ROOT/"canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py")==EXPECTED_ADAPTER,"ADAPTER_BLOB_MISMATCH")

wt=WRAPPER.read_text(); lt=LAUNCHER.read_text()
ast.parse(wt); ast.parse(lt)
require(f'EPOCH_DIGEST="{EXPECTED_EPOCH}"' in wt,"WRAPPER_EPOCH_MISMATCH")
require(f'EPOCH_DIGEST="{EXPECTED_EPOCH}"' in lt,"LAUNCHER_EPOCH_MISMATCH")
require('"canonical/runtime/instruction_constraint_compiler_v1.py":"'+EXPECTED_COMPILER+'"' in wt,"WRAPPER_COMPILER_BINDING")
require('"canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py":"'+EXPECTED_ADAPTER+'"' in wt,"WRAPPER_ADAPTER_BINDING")
require('new="from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as adapter"' in wt,"V2_SUBSTITUTION_MISSING")
require('CLAIM_REF="refs/heads/livebench-v10-claims/"+EPOCH_DIGEST' in lt,"CLAIM_REF_DERIVATION")
require('method="POST"' in lt,"ATOMIC_CREATE_NOT_POST")
require('if e.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")' in lt,"DUPLICATE_NOT_FAIL_CLOSED")
require('if status!=201: fail("ATOMIC_ONE_USE_CLAIM_NOT_201")' in lt,"NON201_NOT_FAIL_CLOSED")
require('activation_blob=os.environ.get("LIVEBENCH_V10_ACTIVATION_BLOB","")' in lt,"ACTIVATION_NOT_BOUND")
i_claim=lt.index("atomic_claim()")
i_import=lt.index("import diagnose_livebench_replay72_v10_formal_routing as diagnostic")
i_run=lt.index("diagnostic.main(authorized=True,activation_blob=activation_blob)")
require(i_claim<i_import<i_run,"LAUNCH_ORDER_INVALID")
for forbidden in ("download_dataset","parse_population","question_id","test.parquet","huggingface.co/datasets"):
    require(forbidden not in lt,"LAUNCHER_TERMINAL_DATA_ACCESS:"+forbidden)
print("PASS:LIVEBENCH_V10_WRAPPER_AND_ATOMIC_LAUNCHER_ZERO_CASE_VERIFICATION")
