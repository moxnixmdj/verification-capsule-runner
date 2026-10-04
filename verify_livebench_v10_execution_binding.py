#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
ACT=ROOT/"subject/livebench_v10_formal_routing_activation.json"
LAUNCHER=ROOT/"launch_livebench_v10_formal_routing_atomic.py"
WRAPPER=ROOT/"diagnose_livebench_replay72_v10_formal_routing.py"
EXPECTED_ACT="38296a76cc45f3c01d1794b24b167afe1a324c80"
EXPECTED_LAUNCHER="d7cd5b5c90f19ef02c1f27afa1629ed6af5500d9"
EXPECTED_WRAPPER="56ea114d59f0309bc14ef0504a44bec1f808e876"
EXPECTED_EPOCH="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def require(x,msg):
    if not x: raise AssertionError(msg)

require(blob(ACT)==EXPECTED_ACT,"ACTIVATION_BLOB_MISMATCH")
require(blob(LAUNCHER)==EXPECTED_LAUNCHER,"LAUNCHER_BLOB_MISMATCH")
require(blob(WRAPPER)==EXPECTED_WRAPPER,"WRAPPER_BLOB_MISMATCH")
j=json.loads(ACT.read_text())
require(j["authority"]["execution"] is True,"EXECUTION_AUTHORITY_FALSE")
require(j["authority"]["replay_existing_prefix"] is True,"REPLAY_AUTHORITY_FALSE")
require(j["authority"]["new_case_exposure"] is False,"NEW_CASE_AUTHORITY_TRUE")
require(j["scope"]["replay_prefix_limit"]==72,"PREFIX_LIMIT_DRIFT")
require(j["scope"]["case_73_or_later"] is False,"CASE73_ALLOWED")
require(j["one_use_epoch"]["epoch_digest_sha256"]==EXPECTED_EPOCH,"EPOCH_DRIFT")
require(j["one_use_epoch"]["maximum_successful_claims"]==1,"CLAIM_COUNT_DRIFT")
require(j["execution"]["launcher_git_blob_sha"]==EXPECTED_LAUNCHER,"ACTIVATION_LAUNCHER_DRIFT")
require(j["execution"]["wrapper_git_blob_sha"]==EXPECTED_WRAPPER,"ACTIVATION_WRAPPER_DRIFT")
print("PASS:LIVEBENCH_V10_EXECUTION_BINDING_EXACT")
