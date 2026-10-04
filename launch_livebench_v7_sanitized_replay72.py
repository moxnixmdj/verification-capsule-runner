#!/usr/bin/env python3
from __future__ import annotations
import hashlib, pathlib
import diagnose_livebench_replay72_v7_sanitized as diagnostic

EXPECTED={
 "diagnose_livebench_replay72_v7_sanitized.py":"e9a5a5937b19e76bf04444c288e3a75113874ed7",
 "livebench_v7_sanitized_classifier.py":"44df7313c83914204299953dda81900fae85ab68",
 "execute_livebench_if_replay72_v4_candidate.py":"2a57ce896ddbd6819246aab8b44d17a00f36b61e",
}
ACTIVATION_BLOB="494706fa9d11c62c144613a9a494159b10fa0b89"

def blob(path:str)->str:
    b=pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for path,sha in EXPECTED.items():
    got=blob(path)
    if got!=sha:
        raise SystemExit(f"FAIL_CLOSED:BLOB_DRIFT:{path}:{got}")

raise SystemExit(diagnostic.main(authorized=True,activation_blob=ACTIVATION_BLOB))
