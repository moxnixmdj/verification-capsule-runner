#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof

ROOT=Path(__file__).resolve().parents[1]
OUT=Path("unknown_domain_v6_subclass_repair2_receipt.json")

EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":"e52858b9fef2d795f72b45cd3ae82ad04344aa91",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"e92dfde05672a249f2dcb71c7ce87fc783142816",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py":"70bbb5a09b1225b60915cc74bf81593516e26f16",
 "canonical/tests/test_unknown_domain_direct_v5.py":"e2ade4b713bb8103ae577de35a35b1caa03bc5a9",
}

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def run_packet(packet):
    assert packet["case_count"]==27
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out["scorer_result"])
        rows.append(out["scorer_result"])
    agg=scorer.aggregate(rows)
    assert agg["all_27_cases_pass"] is True
    return 27

class EvilStr(str):
    def __getattribute__(self,name):
        if name in {"strip","encode"}:
            raise RuntimeError("EVIL_STR_GETATTRIBUTE_"+name)
        return str.__getattribute__(self,name)
    def strip(self,*a,**k):
        raise RuntimeError("EVIL_STR_STRIP")
    def encode(self,*a,**k):
        raise RuntimeError("EVIL_STR_ENCODE")
    def __len__(self):
        raise RuntimeError("EVIL_STR_LEN")

class EvilBytes(bytes):
    def __getattribute__(self,name):
        if name in {"hex"}:
            raise RuntimeError("EVIL_BYTES_GETATTRIBUTE_"+name)
        return bytes.__getattribute__(self,name)
    def __bytes__(self):
        raise RuntimeError("EVIL_BYTES___BYTES__")
    def __buffer__(self,*a,**k):
        raise RuntimeError("EVIL_BYTES___BUFFER__")
    def __len__(self):
        raise RuntimeError("EVIL_BYTES___LEN__")
    def __getitem__(self,*a,**k):
        raise RuntimeError("EVIL_BYTES___GETITEM__")
    def __iter__(self):
        raise RuntimeError("EVIL_BYTES___ITER__")

class FakeStrViaClassProperty:
    @property
    def __class__(self):
        return str

class FakeBytesViaClassProperty:
    @property
    def __class__(self):
        return bytes

got={p:blob(ROOT/p) for p in EXPECTED}
assert got==EXPECTED,{"expected":EXPECTED,"got":got}

# Reproduce the V3 class-spoof failure that invalidates isinstance
# as a load-bearing type-domain gate, then require the runtime-type V4 successor
# to reject those same proxies before any built-in descriptor is invoked.
fake_str=FakeStrViaClassProperty()
fake_bytes=FakeBytesViaClassProperty()
assert isinstance(fake_str,str) is True
assert isinstance(fake_bytes,bytes) is True
assert issubclass(type(fake_str),str) is False
assert issubclass(type(fake_bytes),bytes) is False

fake_str_rejected=False
try:
    g5._canonical_beacon(fake_str)
except g1.UnknownDomainGeneratorError as e:
    assert str(e)=="POST_FREEZE_BEACON_INVALID"
    fake_str_rejected=True
assert fake_str_rejected

fake_bytes_rejected=False
try:
    g5._secret_bytes_total(fake_bytes)
except g1.UnknownDomainGeneratorError as e:
    assert str(e)=="EVALUATOR_SECRET_INVALID"
    fake_bytes_rejected=True
assert fake_bytes_rejected

# Reproduce the exact second-order failure mode that invalidated repair 1.
evil_bytes=EvilBytes(b"B"*32)
buffer_override_reproduced=False
try:
    memoryview(evil_bytes).tobytes()
except RuntimeError as e:
    assert "BUFFER" in str(e)
    buffer_override_reproduced=True
assert buffer_override_reproduced,"EXPECTED_PY312_PLUS_BUFFER_OVERRIDE_COUNTEREXAMPLE_NOT_REPRODUCED"

# The repaired route must bypass every Python-level hook and return an exact
# plain bytes copy of the inherited immutable payload.
materialized=g5._secret_bytes_total(evil_bytes)
assert type(materialized) is bytes
assert materialized==b"B"*32

# Attack accepted str subclasses with attribute, strip, encode, and len hooks.
evil_beacon=EvilStr("A"*16+"\ud800")
evil_secret_str=EvilStr("S"*31+"\udfff")
canon=g5._canonical_beacon(evil_beacon)
assert canon.isascii()
assert canon=="UDIRV5-BEACON-HEX|"+("A"*16+"\ud800").encode("utf-8","surrogatepass").hex()
secret_text=g5._secret_bytes_total(evil_secret_str)
assert type(secret_text) is bytes
assert secret_text==("S"*31+"\udfff").encode("utf-8","surrogatepass")

# Exhaust the historically dangerous surrogate range through the repaired
# subclass-safe string boundary.
surrogates=set()
for cp in range(0xD800,0xE000):
    b=EvilStr("A"*16+chr(cp))
    c=g5._canonical_beacon(b)
    assert c.isascii()
    surrogates.add(c)
assert len(surrogates)==0x800

# Exact 27-case execution for both hostile-secret types.
cases=0
cases+=run_packet(g5._generate(
    beacon=evil_beacon,
    evaluator_secret=evil_secret_str,
    namespace="V6R2-STRSUBCLASS",
))
cases+=run_packet(g5._generate(
    beacon=evil_beacon,
    evaluator_secret=evil_bytes,
    namespace="V6R2-BYTESSUBCLASS",
))
assert cases==54

# Re-attack structural ID collision resistance while using the repaired hostile
# subclass boundary.
old=g1._token
try:
    g1._token=lambda *a,**k:"COLLISION"
    packet=g5._generate(
        beacon=evil_beacon,
        evaluator_secret=evil_bytes,
        namespace="V6R2-COLLIDE",
    )
    assert len({x["case_id"] for x in packet["visible_cases"]})==27
    cases+=run_packet(packet)
finally:
    g1._token=old
assert cases==81

# The proposal itself must prove against the exact repaired blobs only after all
# independent adversarial attacks above have passed.
theorem=proof.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
assert theorem["string_interface_totality"]["genuine_runtime_subclass_override_hooks_bypassed"] is True\nassert theorem["string_interface_totality"]["fake_class_proxy_spoof_rejected"] is True
assert theorem["string_interface_totality"]["bytes_subclass_buffer_protocol_override_bypassed"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_RUNTIME_TYPE_REPAIR_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__INDEPENDENT_CONTENT_BOUND_NON_SPOOFABLE_RUNTIME_TYPE_TOTALITY_AND_27_CASE_EXECUTION__ZERO_CREDIT",
 "python":platform.python_version(),
 "exact_subject_blobs":EXPECTED,
 "attacks":{
   "fake_str_class_proxy_isinstance_spoof_reproduced":True,\n   "fake_str_class_proxy_rejected_by_actual_type_gate":fake_str_rejected,\n   "fake_bytes_class_proxy_isinstance_spoof_reproduced":True,\n   "fake_bytes_class_proxy_rejected_by_actual_type_gate":fake_bytes_rejected,\n   "str_subclass_override_getattribute":True,
   "str_subclass_override_strip":True,
   "str_subclass_override_encode":True,
   "str_subclass_override_len":True,
   "bytes_subclass_override_bytes":True,
   "bytes_subclass_override_buffer_counterexample_reproduced":buffer_override_reproduced,
   "bytes_subclass_override_len":True,
   "bytes_subclass_override_getitem":True,
   "bytes_subclass_override_iter":True,
   "base_bytes_descriptor_full_slice_returns_exact_plain_bytes":True,
   "surrogate_codepoints_exhausted":0x800,
   "forced_total_token_collision_retested":True,
 },
 "adversarial_exact_case_executions":cases,
 "production_or_terminal_cases_generated_read_or_consumed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "hard_nonclaims":[
   "THIS_RECEIPT_DOES_NOT_SELF_PROMOTE_THE_BRAIN_PREDICATE",
   "SEPARATE_FAIL_CLOSED_ROOT3_REPROMOTION_REDUCTION_REMAINS_REQUIRED"
 ]
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True,ensure_ascii=True))
