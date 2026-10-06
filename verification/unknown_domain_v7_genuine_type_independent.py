#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import json
import platform
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v7_genuine_type_proof_v1 as proof

ROOT=Path(__file__).resolve().parents[1]
OUT=Path("unknown_domain_v7_genuine_type_receipt.json")

EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":"e52858b9fef2d795f72b45cd3ae82ad04344aa91",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"d2f529ed9a006f53e75d06ece6f2acb54211b127",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/tests/test_unknown_domain_direct_v5.py":"5b1dc24c7ec65edc32475917349c5d8725b9a655",
 "canonical/runtime/unknown_domain_direct_v7_genuine_type_proof_v1.py":"3d7171b34a19f2600f9c5bb512d116806deba481",
}
FROZEN={
 "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json":"fd586455d582c38c7062ffe735f86cb9f2e803ab",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert len(EXPECTED)==11
assert {p:blob(ROOT/p) for p in EXPECTED}==EXPECTED
assert {p:blob(ROOT/p) for p in FROZEN}==FROZEN

gate_src="".join(inspect.getsource(g5._beacon_gate).split())
secret_src="".join(inspect.getsource(g5._secret_bytes_total).split())
assert "issubclass(type(beacon),str)" in gate_src
assert "issubclass(type(secret),bytes)" in secret_src
assert "issubclass(type(secret),str)" in secret_src
assert "str.strip(beacon)" in gate_src
assert 'str.encode(secret,"utf-8","surrogatepass")' in secret_src
assert "bytes.__getitem__(secret,slice(None))" in secret_src

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
        raise RuntimeError("EVIL_BYTES_GETATTRIBUTE")
    def __bytes__(self):
        raise RuntimeError("EVIL_BYTES_BYTES")
    def __buffer__(self,*a,**k):
        raise RuntimeError("EVIL_BYTES_BUFFER")
    def __len__(self):
        raise RuntimeError("EVIL_BYTES_LEN")
    def __getitem__(self,*a,**k):
        raise RuntimeError("EVIL_BYTES_GETITEM")
    def __iter__(self):
        raise RuntimeError("EVIL_BYTES_ITER")

class FakeStr:
    @property
    def __class__(self):
        return str

class FakeBytes:
    @property
    def __class__(self):
        return bytes

fake_str=FakeStr()
fake_bytes=FakeBytes()
assert isinstance(fake_str,str) is True
assert isinstance(fake_bytes,bytes) is True
assert issubclass(type(fake_str),str) is False
assert issubclass(type(fake_bytes),bytes) is False

for fn,arg,expected in (
    (g5._beacon_gate,fake_str,"POST_FREEZE_BEACON_INVALID"),
    (g5._secret_bytes_total,fake_str,"EVALUATOR_SECRET_INVALID"),
    (g5._secret_bytes_total,fake_bytes,"EVALUATOR_SECRET_INVALID"),
):
    try:
        fn(arg)
    except g1.UnknownDomainGeneratorError as exc:
        assert str(exc)==expected
    else:
        raise AssertionError("CLASS_SPOOF_PROXY_WAS_ADMITTED")

evil_beacon=EvilStr("A"*16+"\ud800")
evil_secret_str=EvilStr("S"*31+"\udfff")
evil_secret_bytes=EvilBytes(b"B"*32)
assert g5._canonical_beacon(evil_beacon).isascii()
assert g5._secret_bytes_total(evil_secret_str)==("S"*31+"\udfff").encode("utf-8","surrogatepass")
materialized=g5._secret_bytes_total(evil_secret_bytes)
assert type(materialized) is bytes
assert materialized==b"B"*32

surrogates={g5._canonical_beacon(EvilStr("A"*16+chr(cp))) for cp in range(0xD800,0xE000)}
assert len(surrogates)==0x800

def run_packet(packet):
    assert packet["case_count"]==27
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out["scorer_result"])
        rows.append(out["scorer_result"])
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True
    return len(rows)

cases=run_packet(g5._generate(beacon=evil_beacon,evaluator_secret=evil_secret_str,namespace="V7-STR"))
cases+=run_packet(g5._generate(beacon=evil_beacon,evaluator_secret=evil_secret_bytes,namespace="V7-BYTES"))

old=g1._token
try:
    g1._token=lambda *a,**k:"COLLISION"
    packet=g5._generate(beacon=evil_beacon,evaluator_secret=evil_secret_bytes,namespace="V7-COLLIDE")
    assert len({x["case_id"] for x in packet["visible_cases"]})==27
    cases+=run_packet(packet)
finally:
    g1._token=old
assert cases==81

theorem=proof.prove(ROOT)
assert theorem["status"]=="PASS__GENUINE_RUNTIME_TYPE_DOMAIN_TOTALITY_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
st=theorem["string_interface_totality"]
assert st["genuine_runtime_subclass_override_hooks_bypassed"] is True
assert st["class_spoof_proxies_rejected_by_real_type_gate"] is True
assert st["bytes_subclass_buffer_protocol_override_bypassed"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V7_GENUINE_TYPE_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__INDEPENDENT_CONTENT_BOUND_GENUINE_TYPE_TOTALITY_AND_CLASS_SPOOF_REJECTION__ZERO_CREDIT",
 "python":platform.python_version(),
 "exact_subject_blobs":EXPECTED,
 "frozen_semantics_blobs":FROZEN,
 "required_properties":{
   "all_eleven_required_subject_blobs_match_exactly":True,
   "v7_proof_executes_and_returns_exact_required_status":True,
   "fake_str_class_spoof_reproduced_and_rejected":True,
   "fake_bytes_class_spoof_reproduced_and_rejected":True,
   "genuine_str_subclass_hooks_attacked":True,
   "genuine_bytes_subclass_hooks_attacked":True,
   "base_bytes_descriptor_full_slice_returns_exact_plain_bytes":True,
   "adversarial_genuine_subclass_exact_case_executions":cases,
   "all_2048_surrogate_codepoints_rechecked":len(surrogates)==2048,
   "forced_total_token_collision_regression_rechecked":True,
   "zero_production_or_terminal_cases_generated_read_or_consumed":True,
   "frozen_protocol_and_evaluator_blobs_match":True,
 },
 "production_or_terminal_cases_generated_read_or_consumed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "hard_nonclaims":[
   "THIS_RECEIPT_DOES_NOT_SELF_PROMOTE_THE_BRAIN_PREDICATE",
   "IMMUTABLE_MAIN_WORKFLOW_SUCCESS_ON_BOTH_REQUIRED_PYTHON_VERSIONS_AND_SEPARATE_ROOT3_REDUCTION_REMAIN_REQUIRED"
 ],
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True,ensure_ascii=True))
