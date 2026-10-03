#!/usr/bin/env python3
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
S=ROOT/"subjects/current26_frontier_v2"
EXPECTED={
 "canonical/runtime/current_26_zero_reality_frontier_v2.py":"a1757008ee6925f493e85c1be79a6e438c3a4b7c",
 "canonical/tests/test_current_26_zero_reality_frontier_v2.py":"07e1991a023e16600dfad86012298ebc58b08fe6",
 "canonical/governance/CURRENT_26_ZERO_REALITY_FRONTIER_V2.json":"352fe17467a8335a348949ce2f2b6fdb6235e9ac",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"bc420c6d1a6caaab7a6d5c257640d3f5797170f5",
 "canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json":"bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
 "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json":"4b5517dbd12978f8ffe481fb775e85592c7790c8",
 "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json":"438e2775b64bee5ed6e792522ab35ebd0d6e1771",
 "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"bed23f2e69d4bc8937d792b07b5812364cf26a85",
 "canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"b5192b1903dc603e75efe92b9a00ced0b2722f8c",
 "canonical/verification/OPUS55_BRAIN_WITNESS_NORMALIZATION_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"0488df0f1c13ace2b25695c48ff65d4654f9c3e2",
 "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
}
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,h in EXPECTED.items():
 p=S/rel; assert blob(p)==h,(rel,blob(p),h)
runtime=S/"canonical/runtime/current_26_zero_reality_frontier_v2.py"
spec=importlib.util.spec_from_file_location("frontier",runtime)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
out=mod.evaluate()
assert out["pass"] is True,out
w=out["live_world"]
assert (w["proved_predicates"],w["unresolved_predicates"])==(12,26)
assert (w["active_zero_reality_requirements"],w["active_nondominated_certificates"],w["zero_reality_covered_predicates"])==(16,13,24)
assert w["primitive_zero_reality_work_units"]==30
assert w["matched_priority_child_facts"]==16
assert (w["current_normalized_targets"],w["current_normalized_witnesses"])==(8,12)
assert w["direct_reality_eligible_predicates"]==["FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
assert w["direct_reality_execution_authorized_now"] is False
assert len(out["active_required_propositions"])==16
assert len(out["matched_child_fact_ids"])==16
assert out["fresh_reality_authority"] is False
gov=json.loads((S/"canonical/governance/CURRENT_26_ZERO_REALITY_FRONTIER_V2.json").read_text())
x=gov["exact_state"]
assert x["active_zero_reality_requirements"]==16
assert x["primitive_zero_reality_work_units"]==30
assert x["matched_priority_child_facts"]==16
assert x["current_normalized_targets"]==8 and x["current_normalized_witnesses"]==12
assert x["direct_reality_execution_authorized_now"] is False
print("CURRENT_26_ZERO_REALITY_FRONTIER_V2_INDEPENDENT_VERIFIED")
