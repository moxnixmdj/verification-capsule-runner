#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def loadj(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def find_behavior(obj,bid):
    if isinstance(obj,dict):
        if obj.get("behavior_id")==bid:
            return obj
        for value in obj.values():
            hit=find_behavior(value,bid)
            if hit is not None:
                return hit
    elif isinstance(obj,list):
        for value in obj:
            hit=find_behavior(value,bid)
            if hit is not None:
                return hit
    return None

reg=loadj("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
protocols=loadj("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
binding=loadj("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
claim=loadj("canonical/governance/TOOL_DISCOVERY_FROZEN_SCOPE_UNIVERSAL_THEOREM_V1.json")

beh=find_behavior(reg,"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")
fam=next(x for x in protocols["protocols"] if x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
assert beh is not None
assert "unknown tool discovery" in fam["task_dimensions"]
assert "frozen tool ecosystems with hidden capability variants" in fam["acceptance"]
assert "available tool schemas/capabilities" in beh["inputs"]
assert "unknown or changing capabilities" in beh["environment_state"]
assert "hidden capability variants" in beh["verification_route"]
assert "TOOL_IDS_AND_DECLARED_COSTS" in binding["information_boundary"]["candidate_visible"]
assert "ACTUAL_TOOL_CAPABILITY_MATRIX" in binding["information_boundary"]["hidden_from_candidate"]
assert "UNKNOWN_CAPABILITY_DISCOVERY_WITHOUT_PREDECLARED_GOLD" in binding["acceptance"]["direct_checks"]
assert "NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS" in binding["source_pool"]["terminal_scope_claim"]
assert binding["route_gates"]["population_or_source_pool_frozen"] is True
assert binding["route_gates"]["information_boundary_frozen"] is True
firewall=set(claim["scope_firewall"])
assert "NO_CLAIM_OF_EXHAUSTING_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEM_IDENTITIES" in firewall
assert "NO_CLAIM_THAT_AN_UNOBSERVABLE_TOOL_WITH_NO_SCHEMA_OR_DISCOVERY_SURFACE_CAN_BE_FOUND" in firewall
assert "NO_FINITE_180_CASE_TRANSPORT" in firewall

cand_path=ROOT/"canonical/runtime/tool_discovery_information_safe_candidate.py"
spec=importlib.util.spec_from_file_location("candidate",cand_path)
candidate=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(candidate)

def run_case(n_tools,n_caps,mask):
    caps=[f"C{i}" for i in range(n_caps)]
    tools=[{"tool_id":f"T{i}","cost":float(i+1),"available":True,"authorized":True} for i in range(n_tools)]
    hidden={}
    bit=0
    for tool in tools:
        supported=set()
        for cap in caps:
            if (mask>>bit)&1:
                supported.add(cap)
            bit+=1
        hidden[tool["tool_id"]]=supported
    receipts=[]
    seen=set()
    for _ in range(n_tools*n_caps+1):
        action=candidate.next_action({
            "required_capabilities":caps,
            "tools":tools,
            "prior_probe_receipts":receipts,
            "version_events":[],
        })
        kind=action.get("action")
        if kind=="PROBE":
            key=(action["tool_id"],action["capability"],0)
            assert key not in seen, ("duplicate_probe",n_tools,n_caps,mask,key)
            seen.add(key)
            receipts.append({
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":action["tool_id"],
                "capability":action["capability"],
                "epoch":0,
                "supported":action["capability"] in hidden[action["tool_id"]],
            })
            continue
        sufficient=[t for t in tools if all(c in hidden[t["tool_id"]] for c in caps)]
        expected=sufficient[0]["tool_id"] if sufficient else None
        if expected is None:
            assert kind=="ESCALATE",(n_tools,n_caps,mask,action)
        else:
            assert kind=="SELECT",(n_tools,n_caps,mask,action,expected)
            assert action["tool_id"]==expected,(n_tools,n_caps,mask,action,expected)
        return
    raise AssertionError(("nontermination",n_tools,n_caps,mask))

count=0
for n_tools in range(1,5):
    for n_caps in range(1,4):
        for mask in range(1 << (n_tools*n_caps)):
            run_case(n_tools,n_caps,mask)
            count+=1

# Explicit admissibility filtering counterexamples.
public={
  "required_capabilities":["C"],
  "tools":[
    {"tool_id":"CHEAP_UNAVAILABLE","cost":0.0,"available":False,"authorized":True},
    {"tool_id":"CHEAP_UNAUTHORIZED","cost":0.1,"available":True,"authorized":False},
    {"tool_id":"VALID","cost":1.0,"available":True,"authorized":True},
  ],
  "prior_probe_receipts":[],
  "version_events":[],
}
a=candidate.next_action(public)
assert a=={"action":"PROBE","tool_id":"VALID","capability":"C"},a

print(json.dumps({
  "status":"PASS__INDEPENDENT_SCOPE_AND_SMALL_STATE_FALSIFICATION",
  "exhaustive_small_state_cases":count,
  "frozen_identity_visibility":True,
  "hidden_capability_state":True,
  "open_domain_identity_exhaustion_claimed":False,
  "target_preserved":True
},sort_keys=True))
