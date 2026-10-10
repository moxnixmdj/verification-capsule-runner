#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"capsules/tb_science_rank15_20261009_v1"
for p in (str(ROOT),str(RUNTIME)):
    if p not in sys.path:
        sys.path.insert(0,p)

from canonical.runtime import harbor_science_agent_v13 as agent
from execution_guard.logical_attempt_identity_v1 import logical_attempt_id as v1
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as v2

SLOT="terminal-bench-science/diag-chipseq::trial-0"
TASK="sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
CLAIM="sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
EXPECTED="a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"
OLD="def7e2921acf58d4ef03e3183512996c718a5a13069482cb825464c0c963a8b4"

assert v1(slot_id=SLOT,task_digest=TASK)==OLD
assert v2(slot_id=SLOT,task_digest=TASK,execution_claim_binding_digest=CLAIM)==EXPECTED
assert OLD!=EXPECTED

base={
    "BRAIN_SLOT_ID":SLOT,
    "BRAIN_TASK_DIGEST":TASK,
    "BRAIN_LOGICAL_ATTEMPT_ID":EXPECTED,
    "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST":CLAIM,
}
saved=dict(os.environ)
try:
    os.environ.clear(); os.environ.update(base)
    assert agent.logical_attempt_id_for_goal("synthetic no-task verification")==EXPECTED
    os.environ["BRAIN_LOGICAL_ATTEMPT_ID"]=OLD
    try:
        agent.logical_attempt_id_for_goal("synthetic no-task verification")
        raise AssertionError("old V1 identity unexpectedly accepted")
    except RuntimeError as exc:
        assert str(exc)=="BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH"
    os.environ.clear(); os.environ.update(base); os.environ.pop("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST")
    try:
        agent.logical_attempt_id_for_goal("synthetic no-task verification")
        raise AssertionError("missing claim digest unexpectedly accepted")
    except RuntimeError as exc:
        assert str(exc)=="BRAIN_EXECUTION_CLAIM_BINDING_DIGEST_REQUIRED"
finally:
    os.environ.clear(); os.environ.update(saved)

print('{"pass":true,"tests":5,"task_read":false,"task_started":false,"benchmark_trials_consumed":0}')
