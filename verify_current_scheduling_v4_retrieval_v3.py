#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,subprocess,sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V4.json":"a17f20106cdb0518339f639b749a9a0b37f001b7",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"f47a69253e7eb75e139b445b736d3d18b33be622",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
 "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py":"73ff5863845402fdd304c0e8c64b4b1d36330f45",
 "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json":"38b53147597b5457859e3b0d031168842560e3e2",
 "canonical/runtime/current_terminal_scheduling_world_v1.py":"9ae2b990578b042dd24074fd5013378b72e64b6b",
 "canonical/tests/test_current_terminal_scheduling_world_v1.py":"856517ca43bf05cd2888bfeeed5e8aea963c6eed",
 "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json":"4b5517dbd12978f8ffe481fb775e85592c7790c8",
 "canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json":"e56719b8c63078273a6974104d413aa1b643da3b",
 "canonical/verification/RETRIEVAL_V3_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"a1bc5d4ef2a767973e48a96ed986f7181630d959"
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
actual={p:blob(ROOT/p) for p in EXPECTED}
assert actual==EXPECTED,{"expected":EXPECTED,"actual":actual}

world=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V4.json").read_text())
assert world["current_authority_inputs"]["current_terminal_authority"]["git_blob_sha"]==EXPECTED["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]
assert world["current_authority_inputs"]["predicate_registry"]["git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"]
assert world["current_authority_inputs"]["evidence_bindings"]["git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"]
for path,sha in world["exact_candidate_blobs"].items():
 assert blob(ROOT/path)==sha,(path,blob(ROOT/path),sha)
assert world["expected_live_world"]["registry_predicates"]==38
assert world["expected_live_world"]["proved_predicates"]==11
assert world["expected_live_world"]["unresolved_predicates"]==27
assert world["expected_live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert world["expected_live_world"]["tool_discovery_retrieval_authority"]=="V3_OVER_VERIFIED_V2_BASE"
assert "NO_SOURCE_EPOCH_EXHAUSTION_BEFORE_V3_EXPANSION_UNLESS_A_VERIFIED_SUFFICIENT_WITNESS_ALREADY_STOPPED_SEARCH" in world["hard_rules"]

cp=subprocess.run([sys.executable,"-m","unittest","-v","canonical.tests.test_current_terminal_scheduling_world_v1"],cwd=ROOT,text=True,capture_output=True)
print(cp.stdout); print(cp.stderr,file=sys.stderr)
assert cp.returncode==0,cp.returncode

from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as gate
from canonical.runtime import current_terminal_scheduling_world_v1 as sched
gate_out=gate.evaluate_repository(ROOT)
assert gate_out["pass"] is True,gate_out
assert gate_out["v3_multilingual_adaptive_federation_mandatory"] is True,gate_out

def load(rel):
 return json.loads((ROOT/rel).read_text())
out=sched.evaluate(
 load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
 load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
 load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
 load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
 load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
 load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
 gate_out,
)
assert out["pass"] is True,out
assert out["registry_predicate_count"]==38,out
assert out["proved_predicate_count"]==11,out
assert out["unresolved_predicate_count"]==27,out
assert out["live_action_coverage_count"]==27,out
assert out["tool_discovery_retrieval_authority_gate_pass"] is True,out
assert "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in out["unresolved_predicates"],out
assert out["execution_authority"] is False and out["promotion_authority"] is False,out

without=sched.evaluate(
 load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
 load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
 load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
 load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
 load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
 load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
)
assert without["pass"] is False,without
assert "TOOL_DISCOVERY_RETRIEVAL_AUTHORITY_GATE_NOT_PASS" in without["errors"],without

print("CURRENT_SCHEDULING_V4_RETRIEVAL_V3_VERIFIED")
print(json.dumps({
 "exact_blobs":actual,
 "registry_predicates":38,
 "proved_predicates":11,
 "unresolved_predicates":27,
 "opus55_acceptance":"4/19_PASS__15/19_OPEN",
 "retrieval_v3_gate_mandatory":True,
 "scheduler_without_gate_fails_closed":True,
 "zero_credit":True
},sort_keys=True))
