#!/usr/bin/env python3
from __future__ import annotations
import hashlib, pathlib, sys, unittest

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
