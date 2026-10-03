#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,subprocess,sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py":"73ff5863845402fdd304c0e8c64b4b1d36330f45",
 "canonical/tests/test_tool_discovery_retrieval_authority_gate_v1.py":"4028160b0ab81f59ab8095419a74272e832e9844",
 "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json":"38b53147597b5457859e3b0d031168842560e3e2",
 "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1.json":"4fde285b62a3a84e7f12852d8600aecfc01bab81",
 "canonical/verification/RETRIEVAL_V3_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"5ab1f983a6f373bb29680e14d83c3e83cd2c0d68",
 "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1.json":"c916c095cfb52b4b3d8dd863dfb0be0f05529f2e",
 "canonical/verification/TOOL_DISCOVERY_RETRIEVAL_FRONTIER_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"bbbd34e192aa65ba94c4bda19a1a1eb9c2b5b406",
 "canonical/runtime/residual_witness_retrieval_compiler_v1.py":"9daa8d590f3356b3fc51eccf75c56cbf515239e4",
 "canonical/verification/RESIDUAL_WITNESS_RETRIEVAL_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"f0a68c8219d704875535543060f63b9ecaca6dd5",
 "canonical/runtime/residual_witness_backend_router_v1.py":"578c5f87901a458b12d7df984e0a6a525d367456",
 "canonical/runtime/github_public_retrieval_provider_v1.py":"29b808935559382ab7ddc81aaa08fe0611a05df8",
 "canonical/verification/GITHUB_PUBLIC_RETRIEVAL_SURFACES_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"ca5acd7afbf14b7cce568ec482c160c3795e57ba"
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

actual={p:blob(ROOT/p) for p in EXPECTED}
assert actual==EXPECTED,{"expected":EXPECTED,"actual":actual}

cp=subprocess.run([sys.executable,"-m","unittest","-v","canonical.tests.test_tool_discovery_retrieval_authority_gate_v1"],cwd=ROOT,text=True,capture_output=True)
print(cp.stdout); print(cp.stderr,file=sys.stderr)
assert cp.returncode==0,cp.returncode

from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as gate
out=gate.evaluate_repository(ROOT)
assert out["pass"] is True,out
assert out["v3_multilingual_adaptive_federation_mandatory"] is True,out
assert out["unknown_preserved"] is True,out
assert out["same_epoch_replay_disabled"] is True,out
assert out["acceptance_credit"]==0,out
assert out["execution_authority"] is False and out["promotion_authority"] is False,out

print("RETRIEVAL_V3_LIVE_GATE_VERIFIED")
print(json.dumps({
 "exact_blobs":actual,
 "gate_pass":True,
 "v3_mandatory":True,
 "unknown_preserved":True,
 "same_epoch_replay_disabled":True,
 "zero_credit":True
},sort_keys=True))
