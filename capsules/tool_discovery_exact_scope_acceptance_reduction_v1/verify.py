from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\\0".encode()+b).hexdigest()

exp=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
paths={
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":ROOT/"protocols.json",
 "canonical/governance/OPUS55_TOOL_DISCOVERY_SCOPE_COMPLETE_ACCEPTANCE_INPUT_V1.json":ROOT/"acceptance_input.json",
 "canonical/runtime/acceptance_proof_transmuter_v1.py":ROOT/"transmuter.py",
 "canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json":ROOT/"source_witness.json",
 "canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":ROOT/"scope_receipt.json",
}
actual={k:blob(v) for k,v in paths.items()}
assert actual==exp["exact_brain_blobs"],(actual,exp["exact_brain_blobs"])

protocols=json.loads((ROOT/"protocols.json").read_text())
inp=json.loads((ROOT/"acceptance_input.json").read_text())
source=json.loads((ROOT/"source_witness.json").read_text())
scope=json.loads((ROOT/"scope_receipt.json").read_text())

assert len(protocols["protocols"])==19
prior_closed=[x["family"] for x in protocols["protocols"] if x.get("status")=="PASS"]
assert prior_closed==[
 "LONG_HORIZON_MEMORY_AND_CONTINUITY",
 "SUBAGENT_DELEGATION_AND_COORDINATION",
 "EXACT_SYMBOLIC_COMPUTATION",
],prior_closed

assert scope["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert scope["public_runner"]["conclusion"]=="success"
assert scope["target_family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
assert scope["target_predicate"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
assert scope["basis_kind"]=="EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
assert scope["proof_domain"]=="EXACT_FROZEN_TOOL_DISCOVERY_TERMINAL_TARGET_ONLY"
assert scope["scope_semantics_discharged"] is True
assert scope["complete_target_case_set"] is True
assert "NO_CLAIM_OF_EXHAUSTIVE_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS" in scope["hard_nonclaims"]
assert scope["new_reality_units_consumed"]==0 and scope["terminal_cases_replayed"]==0

assert len(inp["evidence"])==1
embedded=copy.deepcopy(inp["evidence"][0])
sc=embedded.pop("scope_completeness")
assert embedded==source,(embedded,source)
assert sc=={
 "verified":True,
 "independent":True,
 "basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
 "complete_target_case_set":True,
 "receipt":"canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
assert inp["scope_completeness_receipt"]==sc["receipt"]

assert source["id"]=="TOOL_DISCOVERY_TERMINAL_CEILING_ABSOLUTE_DOMINANCE_20261002_V1"
assert source["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
assert source["mode"]=="ABSOLUTE_DOMINANCE"
assert source["verified"] is True and source["independent"] is True
assert source["contamination_clean"] is True
assert source["binds_frozen_protocol"] is True
assert source["scope_relation"]=="PROVEN_STRONGER"
assert source["closes_entire_protocol"] is True
assert source["source_case_count"]==180
assert source["result"]=={"direction":"higher","brain_lower_bound":1,"theoretical_upper_bound":1}

spec=importlib.util.spec_from_file_location("transmuter",ROOT/"transmuter.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out=mod.evaluate(protocols,inp)
assert out["status"]=="PASS",out
assert out["family_count"]==19
assert out["closed_family_count"]==4
assert out["open_family_count"]==15
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
assert out["execution_authority"] is False and out["promotion_authority"] is False

rows={x["family"]:x for x in out["families"]}
new=[f for f,r in rows.items() if f not in prior_closed and r["result_status"]=="PASS"]
assert new==["TOOL_DISCOVERY_SELECTION_AND_LEARNING"],new
for f in prior_closed:
    assert rows[f]["result_status"]=="PASS" and rows[f]["closure_mode"]=="ALREADY_PASS"
td=rows["TOOL_DISCOVERY_SELECTION_AND_LEARNING"]
assert td["input_status"]=="DEFINED_RESULT_OPEN"
assert td["result_status"]=="PASS"
assert td["closure_mode"]=="ABSOLUTE_DOMINANCE"
assert td["witness_id"]=="TOOL_DISCOVERY_TERMINAL_CEILING_ABSOLUTE_DOMINANCE_20261002_V1"
assert td["witness_reason"]=="THEORETICAL_CEILING_DOMINANCE"

for fam,row in rows.items():
    if fam not in prior_closed+["TOOL_DISCOVERY_SELECTION_AND_LEARNING"]:
        assert row["result_status"]=="DEFINED_RESULT_OPEN",(fam,row)

expect=inp["expected_compile_result"]
assert expect["family_count"]==19
assert expect["closed_family_count"]==4
assert expect["open_family_count"]==15
assert expect["newly_closed_families"]==["TOOL_DISCOVERY_SELECTION_AND_LEARNING"]
assert set(expect["preserved_closed_families"])==set(prior_closed)

print(json.dumps({
 "status":"PASS",
 "prior_closed_family_count":3,
 "new_closed_family_count":4,
 "newly_closed_families":["TOOL_DISCOVERY_SELECTION_AND_LEARNING"],
 "scope_basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
 "terminal_replay":0,
 "new_reality":0,
 "acceptance_compiler_output":out
},indent=2,sort_keys=True))
