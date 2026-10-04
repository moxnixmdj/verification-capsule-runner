#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,re

ROOT=pathlib.Path(__file__).resolve().parent
LAUNCHER=ROOT/"launch_livebench_v10_formal_routing_atomic.py"
ACT=ROOT/"LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json"
WRAPPER=ROOT/"diagnose_livebench_replay72_v10_formal_routing.py"

EXPECTED={
 "launch_livebench_v10_formal_routing_atomic.py":"2d3b9ad4e3f4f02af56f402733a8d8bb04ab79c0",
 "LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json":"7a2c2fdc3cc08862850a13667ee2cd2b2e2aae91",
 "diagnose_livebench_replay72_v10_formal_routing.py":"56ea114d59f0309bc14ef0504a44bec1f808e876",
}
EPOCH="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"
CANDIDATE="7d42814e46abda96eed0fb1929bef5a829bd2236"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,want in EXPECTED.items():
    p=ROOT/rel
    if not p.is_file() or blob(p)!=want:
        raise SystemExit("FAIL_CLOSED:BLOB_MISMATCH:"+rel)

doc=json.loads(ACT.read_text(encoding="utf-8"))
checks=[
 doc.get("schema")=="PROJECT_BRAIN_LIVEBENCH_V10_REPLAY72_ACTIVATION_V1",
 doc.get("target_predicate")=="LIVEBENCH_IF_GE_65_7",
 doc.get("epoch_digest_sha256")==EPOCH,
 doc.get("candidate_git_blob_sha")==CANDIDATE,
 doc.get("wrapper_git_blob_sha")==EXPECTED["diagnose_livebench_replay72_v10_formal_routing.py"],
 doc.get("launcher_git_blob_sha")==EXPECTED["launch_livebench_v10_formal_routing_atomic.py"],
 doc.get("authority",{}).get("replay72") is True,
 doc.get("authority",{}).get("new_case_exposure") is False,
 doc.get("authority",{}).get("fresh_reality") is False,
 doc.get("authority",{}).get("promotion") is False,
 doc.get("authority",{}).get("acceptance_credit") is False,
 doc.get("replay_scope",{}).get("already_exposed_prefix_only") is True,
 doc.get("replay_scope",{}).get("replay_prefix_limit")==72,
 doc.get("replay_scope",{}).get("case_73_or_later") is False,
]
if not all(checks): raise SystemExit("FAIL_CLOSED:ACTIVATION_SEMANTICS")
text=LAUNCHER.read_text(encoding="utf-8")
if 'ACTIVATION_FILENAME = "LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json"' not in text:
    raise SystemExit("FAIL_CLOSED:ACTIVATION_FILENAME")
main_text=text[text.index("def main():"):]
if "verify_exact_activation()" not in main_text or not main_text.index("verify_exact_activation()") < main_text.index("atomic_claim()"):
    raise SystemExit("FAIL_CLOSED:ACTIVATION_BEFORE_CLAIM_ORDER")
if not main_text.index("atomic_claim()") < main_text.index("import diagnose_livebench_replay72_v10_formal_routing as diagnostic"):
    raise SystemExit("FAIL_CLOSED:CLAIM_BEFORE_REPLAY_ORDER")
if 'if exc.code == 422:' not in text:
    raise SystemExit("FAIL_CLOSED:DUPLICATE_NOT_FAIL_CLOSED")
print("PASS:LIVEBENCH_V10_CONTENT_ADDRESSED_EXECUTION_BINDING")
