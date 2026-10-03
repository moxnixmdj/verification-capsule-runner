#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subjects/retrieval_v4"
FILES={
 "federation_v1":("canonical/runtime/public_source_federation_v1.py","3f69b3e8371fe3e5abc173c6c9fe17e9003a938b"),
 "federation_v2":("canonical/runtime/public_source_federation_v2.py","32f0443bfb1859168e14f7266a3b5b3c99a40f45"),
 "compiler":("canonical/runtime/residual_witness_retrieval_compiler_v1.py","9daa8d590f3356b3fc51eccf75c56cbf515239e4"),
 "router":("canonical/runtime/residual_witness_backend_router_v1.py","578c5f87901a458b12d7df984e0a6a525d367456"),
 "epoch_gate":("canonical/runtime/federated_retrieval_epoch_gate_v1.py","0a36836c8f0428338a9931b757090a26f73c2672"),
 "tests":("canonical/tests/test_retrieval_v4_federated_epoch_gate.py","c89f60ad64da2933a1a2a6b617f1daef7c18c0e4"),
}
def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for name,(rel,expected) in FILES.items():
    actual=blob(SUB/rel)
    assert actual==expected,(name,actual,expected)

sys.path.insert(0,str(SUB))
suite=unittest.defaultTestLoader.loadTestsFromName("canonical.tests.test_retrieval_v4_federated_epoch_gate")
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful()
print("RETRIEVAL_V4_FEDERATION_EPOCH_GATE_VERIFIED")
print("exact_blobs="+repr({k:v[1] for k,v in FILES.items()}))

# Retrieval V4 activation authority checks.
ACT_ROOT=ROOT/"subjects/retrieval_v4_activation"
def act_blob(name):
    raw=(ACT_ROOT/name).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
assert act_blob("TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V4_ACTIVATION_V1.json")=="643890c1d09844ea49de434df8ffec02962806e4"
assert act_blob("RETRIEVAL_V4_FEDERATION_EPOCH_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")=="4473b60853e1584bae8933099256c92c9e1676e4"
assert act_blob("TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1.json")=="4fde285b62a3a84e7f12852d8600aecfc01bab81"
v4=json.loads((ACT_ROOT/"TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V4_ACTIVATION_V1.json").read_text())
vr=json.loads((ACT_ROOT/"RETRIEVAL_V4_FEDERATION_EPOCH_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())
assert v4["base_retrieval_authority"]["git_blob_sha"]=="4fde285b62a3a84e7f12852d8600aecfc01bab81"
assert v4["base_retrieval_authority"]["rule"]=="V3_REMAINS_MANDATORY_AND_IS_NOT_WEAKENED"
assert v4["v4_verified_extension"]["verification_git_blob_sha"]=="4473b60853e1584bae8933099256c92c9e1676e4"
assert vr["independent_runner"]["conclusion"]=="success"
assert vr["verified"]["source_group_count"]==14
assert vr["verified"]["epoch_consumption_requires_one_router_receipt_per_selected_cell"] is True
assert vr["verified"]["missing_receipt_fails_closed"] is True
assert vr["verified"]["unbound_backend_does_not_count_as_attempt"] is True
assert vr["verified"]["failed_or_empty_attempts_preserve_unknown"] is True
assert vr["verified"]["epoch_consumption_does_not_authorize_nonexistence"] is True
assert "V4_EXTENDS_V3_AND_CANNOT_BYPASS_OR_WEAKEN_V3" in v4["hard_rules"]
assert "NO_SOURCE_EPOCH_CONSUMPTION_WITH_MISSING_ROUTER_RECEIPTS" in v4["hard_rules"]
assert v4["stop_rules"]["no_witness_and_open_world_scope_not_complete"]=="UNKNOWN__DO_NOT_INFER_NONEXISTENCE"
print("RETRIEVAL_V4_ACTIVATION_VERIFIED")

# Live Tool Discovery retrieval gate checks.
LIVE=ROOT/"subjects/retrieval_v4_live"
def live_blob(name):
    raw=(LIVE/name).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
assert live_blob("tool_discovery_retrieval_authority_gate_v1.py")=="b01292c1f198f251b8a9606b4de173541204c2dc"
assert live_blob("OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")=="38b53147597b5457859e3b0d031168842560e3e2"
spec=importlib.util.spec_from_file_location("retrieval_v4_live_gate",LIVE/"tool_discovery_retrieval_authority_gate_v1.py")
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
def jl(name): return json.loads((LIVE/name).read_text())
hyper=jl("OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
v2=jl("V2_ACTIVATION.json"); v2v=jl("V2_ACTIVATION_VERIFICATION.json")
cv=jl("COMPILER_VERIFICATION.json"); bv=jl("BACKEND_VERIFICATION.json")
v3=jl("V3_ACTIVATION.json"); v3v=jl("V3_ACTIVATION_VERIFICATION.json")
v4a=jl("V4_ACTIVATION.json"); v4av=jl("V4_ACTIVATION_VERIFICATION.json")
actual={
 "activation_blob":"c916c095cfb52b4b3d8dd863dfb0be0f05529f2e",
 "activation_verification_blob":"bbbd34e192aa65ba94c4bda19a1a1eb9c2b5b406",
 "compiler_blob":"9daa8d590f3356b3fc51eccf75c56cbf515239e4",
 "compiler_verification_blob":"f0a68c8219d704875535543060f63b9ecaca6dd5",
 "router_blob":"578c5f87901a458b12d7df984e0a6a525d367456",
 "github_provider_blob":"29b808935559382ab7ddc81aaa08fe0611a05df8",
 "backend_verification_blob":"ca5acd7afbf14b7cce568ec482c160c3795e57ba",
 "v3_activation_blob":"4fde285b62a3a84e7f12852d8600aecfc01bab81",
 "v3_activation_verification_blob":"5ab1f983a6f373bb29680e14d83c3e83cd2c0d68",
 "v4_activation_blob":"643890c1d09844ea49de434df8ffec02962806e4",
 "v4_activation_verification_blob":"e35dc954e0cf892d5522e62b5948bb64edeed4f7",
}
def live_check(h=hyper,a4=v4a,a4v=v4av,blobs=actual):
    return gate.validate(h,v2,v2v,cv,bv,v3,v3v,a4,a4v,blobs)
g=live_check()
assert g["pass"] is True,g
assert g["v4_federated_router_receipts_mandatory"] is True,g
mut=dict(actual); mut["v4_activation_blob"]="0"*40
assert "ACTUAL_BLOB_MISMATCH:v4_activation_blob" in live_check(blobs=mut)["errors"]
m=copy.deepcopy(v4a); m["stop_rules"]["missing_or_unbound_router_receipt"]="IGNORE"
assert "V4_MISSING_RECEIPT_STOP_RULE_INVALID" in live_check(a4=m)["errors"]
m=copy.deepcopy(v4av); m["independent_runner"]["conclusion"]="failure"
assert "V4_ACTIVATION_INDEPENDENT_RUNNER_NOT_SUCCESS" in live_check(a4v=m)["errors"]
m=copy.deepcopy(hyper); a=next(x for x in m["actions"] if gate.TARGET in x.get("target_predicates",[])); d=copy.deepcopy(a); d["id"]="SECOND_TOOL_DISCOVERY_ROUTE"; m["actions"].append(d)
assert any(x.startswith("TOOL_DISCOVERY_TARGET_ACTION_COUNT_NE_1:") for x in live_check(h=m)["errors"])
print("RETRIEVAL_V4_LIVE_GATE_VERIFIED")
