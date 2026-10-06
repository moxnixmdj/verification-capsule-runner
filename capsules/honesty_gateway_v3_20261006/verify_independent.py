from __future__ import annotations

import base64
import hashlib
import importlib
import json
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
MANIFEST=json.loads((HERE/"MANIFEST.json").read_text())

def decode(name:str)->bytes:
    return base64.b64decode((HERE/"blobs"/name).read_text())

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

gateway=decode("honesty_emission_gateway_v3.py.b64")
envelope=decode("honesty_envelope_v1.py.b64")
brain_tests=decode("test_honesty_emission_gateway_v3.py.b64")
assert git_blob_sha(gateway)==MANIFEST["runtime_sha"]
assert git_blob_sha(envelope)==MANIFEST["envelope_sha"]
assert git_blob_sha(brain_tests)==MANIFEST["test_sha"]
assert b"honesty_emission_gateway_v1" not in gateway
assert b"honesty_emission_gateway_v2" not in gateway

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    runtime=root/"canonical"/"runtime"; tests=root/"canonical"/"tests"
    runtime.mkdir(parents=True); tests.mkdir(parents=True)
    (runtime/"honesty_emission_gateway_v3.py").write_bytes(gateway)
    (runtime/"honesty_envelope_v1.py").write_bytes(envelope)
    (runtime/"zero_ambient_namespace_launcher_v1.py").write_text(
        "def run_confined(policy):\n    raise RuntimeError('IMPORT_SHIM_ONLY')\n"
    )
    (tests/"test_honesty_emission_gateway_v3.py").write_bytes(brain_tests)
    sys.path.insert(0,str(root))
    g=importlib.import_module("canonical.runtime.honesty_emission_gateway_v3")
    t=importlib.import_module("canonical.tests.test_honesty_emission_gateway_v3")

    brain_test_count=0
    for name in sorted(dir(t)):
        fn=getattr(t,name)
        if name.startswith("test_") and callable(fn):
            fn(); brain_test_count+=1

    R="b"*64
    def rec():
        return {
          "schema":"PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
          "task_contract":{"task_id":"I","required_obligations":["O"]},
          "obligations":[{"id":"O","state":"VERIFIED","receipts":[R]}],
          "completion_claim":"COMPLETE",
          "provenance_events":[],"material_claims":[],"belief_assertions":[]
        }

    def expect_fail(raw:bytes):
        try: g.adjudicate_broker_payload(raw)
        except Exception: return
        raise AssertionError("expected fail-closed")

    expect_fail(b'{"status":"COMPLETE"}\n')

    a=g.make_capsule(sequence=0,emission_id="A",payload={"x":1},honesty_record=rec())
    c=g.make_capsule(sequence=2,emission_id="C",payload={"x":3},honesty_record=rec())
    expect_fail(g.encode_capsule(a)+g.encode_capsule(c))

    b=g.make_capsule(sequence=1,emission_id="A",payload={"x":2},honesty_record=rec())
    expect_fail(g.encode_capsule(a)+g.encode_capsule(b))

    replay=g.make_capsule(sequence=1,emission_id="B",payload={"x":2},honesty_record=rec())
    replay["honesty_record"]=a["honesty_record"]
    replay["honesty_record_sha256"]=g._sha(replay["honesty_record"])
    expect_fail(g.encode_capsule(a)+g.encode_capsule(replay))

    valid=g.encode_capsule(a)
    def runner(status="CHILD_EXITED",rc=0,effects=0,sha=None,n=None):
        return lambda _:{
          "status":status,"returncode":rc,"material_effects_committed":effects,
          "policy_sha256":"p","broker_payload":valid,
          "broker_bytes":len(valid) if n is None else n,
          "broker_sha256":hashlib.sha256(valid).hexdigest() if sha is None else sha
        }

    good=g.run({},confined_runner=runner())
    assert good["status"]=="PASS__CONTENT_BOUND_HONESTY_EMISSIONS_ONLY"
    assert good["emission_count"]==1
    assert good["raw_broker_exposed"] is False
    assert "broker_payload" not in good

    for bad_runner in (
        runner(status="WALLCLOCK_LIMIT_EXCEEDED",rc=9),
        runner(rc=7),
        runner(effects=1),
        runner(sha="0"*64),
        runner(n=len(valid)+1),
    ):
        out=g.run({},confined_runner=bad_runner)
        assert out["status"]=="FAIL_CLOSED"
        assert out["emissions"]==[]
        assert out["raw_broker_exposed"] is False

print("PASS",json.dumps({
  "brain_tests":brain_test_count,
  "independent_raw_replay_sequence_and_exit_falsifiers":"PASS",
  "runtime_sha":MANIFEST["runtime_sha"],
  "credit_delta":0
},sort_keys=True))
