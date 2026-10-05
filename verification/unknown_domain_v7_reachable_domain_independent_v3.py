#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_production_once_v1 as prod
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof

ROOT=Path(__file__).resolve().parents[1]
OUT=Path("unknown_domain_v7_reachable_domain_receipt.json")

EXPECTED_SUBJECT={
 "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"0faa62fce4bc2f2a99c173b0a10a32d5e1c6a244",
 "canonical/tests/test_unknown_domain_direct_v5.py":"1961cff0013ff9f17feca981409d89d01ecf6769",
 "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py":"2da564d27a318a99713165208126aaaf36ebc924",
}
EXPECTED_LAUNCHER={
 "canonical/runtime/unknown_domain_direct_production_once_v1.py":"7f05674904a4b3223cb26993a1e2e4b0bac8a0e7",
 ".github/workflows/unknown-domain-direct-one-use-production.yml":"990b4fe712ca509f3e01c8e632c75416a3cd0b98",
}

def blob(p:Path)->str:
    # Hash the Git object, not checkout bytes. Windows checkout may materialize
    # CRLF while the frozen subject is defined by the repository blob identity.
    rel=p.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git","rev-parse",f"HEAD:{rel}"],
        cwd=ROOT,
        text=True,
    ).strip()

def run_packet(packet):
    rows=[]
    assert packet["case_count"]==27
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out["scorer_result"])
        rows.append(out["scorer_result"])
    agg=scorer.aggregate(rows)
    assert agg["all_27_cases_pass"] is True
    return len(rows)

got_subject={p:blob(ROOT/p) for p in EXPECTED_SUBJECT}
got_launcher={p:blob(ROOT/p) for p in EXPECTED_LAUNCHER}
assert got_subject==EXPECTED_SUBJECT,(got_subject,EXPECTED_SUBJECT)
assert got_launcher==EXPECTED_LAUNCHER,(got_launcher,EXPECTED_LAUNCHER)

# Execute the exact frozen production constructor with all case generation and
# scoring stubbed out. This proves the values that cross the generator boundary
# are exact built-in types without consuming any production/terminal case.
captured={}
orig_generate=prod.generator.generate_production_population
orig_evaluate=prod.evaluate_packet
try:
    def fake_generate(*,beacon,evaluator_secret,authority):
        captured["beacon"]=beacon
        captured["secret"]=evaluator_secret
        captured["authority"]=dict(authority)
        return {
            "production":True,
            "case_count":27,
            "authority_claim_id":authority["one_use_claim_id"],
            "visible_packet_digest":"stub-visible",
            "hidden_packet_digest":"stub-hidden",
        }
    def fake_evaluate(packet):
        captured["packet"]=dict(packet)
        return {"case_results":[],"aggregate":{"all_27_cases_pass":True}}
    prod.generator.generate_production_population=fake_generate
    prod.evaluate_packet=fake_evaluate
    launcher_result=prod.execute_after_claim(claim_id="refs/heads/unknown-domain-direct-claims/V7TYPEPROOF")
finally:
    prod.generator.generate_production_population=orig_generate
    prod.evaluate_packet=orig_evaluate

assert type(captured["beacon"]) is str
assert captured["beacon"].startswith("UDIR-PROD-")
assert len(captured["beacon"])==58
assert type(captured["secret"]) is bytes
assert len(captured["secret"])==32
assert launcher_result["production_cases_generated"]==27  # declaration only; stub generated zero
assert captured["packet"]["visible_packet_digest"]=="stub-visible"

# Attack the exact previous theorem bug: __class__ spoof proxies fool isinstance
# but must be rejected by V7 before any descriptor/buffer operation.
class FakeStr:
    @property
    def __class__(self):
        return str
class FakeBytes:
    @property
    def __class__(self):
        return bytes
class EvilStr(str):
    def strip(self,*a,**k):
        raise RuntimeError("MUST_NOT_RUN")
    def encode(self,*a,**k):
        raise RuntimeError("MUST_NOT_RUN")
class EvilBytes(bytes):
    def __bytes__(self):
        raise RuntimeError("MUST_NOT_RUN")
    def __getitem__(self,*a,**k):
        raise RuntimeError("MUST_NOT_RUN")

fake_s=FakeStr(); fake_b=FakeBytes()
assert isinstance(fake_s,str) is True and type(fake_s) is not str
assert isinstance(fake_b,bytes) is True and type(fake_b) is not bytes

rejected=[]
for name,fn in [
    ("fake_beacon",lambda:g5._canonical_beacon(fake_s)),
    ("fake_str_secret",lambda:g5._secret_bytes_total(fake_s)),
    ("fake_bytes_secret",lambda:g5._secret_bytes_total(fake_b)),
    ("real_str_subclass_beacon",lambda:g5._canonical_beacon(EvilStr("A"*16))),
    ("real_str_subclass_secret",lambda:g5._secret_bytes_total(EvilStr("S"*32))),
    ("real_bytes_subclass_secret",lambda:g5._secret_bytes_total(EvilBytes(b"B"*32))),
]:
    try:
        fn()
    except g1.UnknownDomainGeneratorError:
        rejected.append(name)
    else:
        raise AssertionError("UNREACHABLE_DOMAIN_WIDENING_ACCEPTED:"+name)
assert len(rejected)==6

# Exact reachable built-in values execute the full bound evaluator.
cases=run_packet(g5._generate(
    beacon="UDIR-PROD-"+"a"*48,
    evaluator_secret=b"S"*32,
    namespace="V7-REACHABLE-INDEPENDENT",
))
assert cases==27

# Preserve surrogate totality on the exact built-in nonproduction str path.
seen=set()
for cp in range(0xD800,0xE000):
    value="A"*16+chr(cp)
    assert type(value) is str
    out=g5._canonical_beacon(value)
    assert out.isascii()
    seen.add(out)
assert len(seen)==2048

# Preserve the structural collision theorem under the repaired domain.
old=g1._token
try:
    g1._token=lambda *a,**k:"COLLISION"
    packet=g5._generate(
        beacon="UDIR-PROD-"+"b"*48,
        evaluator_secret=b"T"*32,
        namespace="V7-COLLIDE",
    )
    assert len({x["case_id"] for x in packet["visible_cases"]})==27
    cases+=run_packet(packet)
finally:
    g1._token=old
assert cases==54

theorem=proof.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR"
st=theorem["string_interface_totality"]
assert st["reachable_production_type_domain_total"] is True
assert st["isinstance_class_spoof_domain_rejected"] is True
assert st["real_subclass_widening_rejected"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V7_REACHABLE_DOMAIN_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__CONTENT_BOUND_FROZEN_LAUNCHER_REACHABLE_TYPE_DOMAIN__CLASS_SPOOF_REJECTED__54_NONPRODUCTION_CASES__ZERO_TERMINAL_REALITY",
 "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
 "exact_subject_blobs":EXPECTED_SUBJECT,
 "exact_launcher_blobs":EXPECTED_LAUNCHER,
 "launcher_boundary":{
   "beacon_exact_type":"str",
   "beacon_prefix":"UDIR-PROD-",
   "evaluator_secret_exact_type":"bytes",
   "evaluator_secret_length":32,
   "production_or_terminal_cases_actually_generated":0,
 },
 "attacks":{
   "fake___class___str_proxy_rejected":True,
   "fake___class___bytes_proxy_rejected":True,
   "real_str_subclass_widening_rejected":True,
   "real_bytes_subclass_widening_rejected":True,
   "surrogate_codepoints_exhausted":2048,
   "forced_total_token_collision_retested":True,
 },
 "nonproduction_exact_scorer_cases":cases,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "hard_nonclaims":[
   "THIS_RECEIPT_DOES_NOT_SELF_PROMOTE_THE_PREDICATE",
   "SEPARATE_FAIL_CLOSED_ROOT3_ACCEPTANCE_REDUCTION_REQUIRED",
   "NO_OPEN_WORLD_CLAIM_BEYOND_THE_FROZEN_EVALUATOR_AND_REACHABLE_LAUNCHER_DOMAIN"
 ]
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
