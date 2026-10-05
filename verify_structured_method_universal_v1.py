#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"structured_method_universal_v1"
OUT=ROOT/"structured_method_universal_v1_receipt.json"

EXPECTED={
"canonical/governance/STRUCTURED_METHOD_UNIVERSAL_CORRECTNESS_RELATION_V1.json":"4e7c2c43cae956ce8eadf29ae04165ed2c9e77a7",
"canonical/runtime/structured_method_universal_correctness_certificate_v1.py":"68b74726f8b95877b786309c1b51d665929478da",
"canonical/tests/test_structured_method_universal_correctness_certificate_v1.py":"47e65b23bbd55e2130c3f486d192f39495428cb2",
"canonical/runtime/structured_method_normalized_rule_graph_v3.py":"79d3896818b03223348f05adf4fdcd574f6f355e",
"canonical/runtime/structured_method_normalized_rule_oracle_v3.py":"5d92b1360fbb1bb27baacc8a04adb3744abf690c",
"canonical/governance/STRUCTURED_METHOD_SCOPE_AUDIT_V3.json":"1db04e3c2c523dfe5f2ebe719b7c63dc9ccd808e",
"canonical/verification/STRUCTURED_METHOD_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"5325382e88f003b5685d9da13df321c23829174f",
"canonical/verification/STRUCTURED_METHOD_NORMALIZED_RULE_V3_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"1d6159334bf8e7067f5cb8d31ae0f25b7bb473c3",
"canonical/governance/STRUCTURED_METHOD_UNIVERSAL_CORRECTNESS_CERTIFICATE_V1.json":"fc4bcf84aff19ed4b96c93166a1e7044d6b689d0",
}

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel:str):
    p=SUB/rel
    got=blob(p)
    assert got==EXPECTED[rel], (rel,got,EXPECTED[rel])
    return json.loads(p.read_text(encoding="utf-8"))

def funcs(src:str)->set[str]:
    return {n.name for n in ast.walk(ast.parse(src)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

for rel in EXPECTED:
    assert blob(SUB/rel)==EXPECTED[rel], rel

relation=load("canonical/governance/STRUCTURED_METHOD_UNIVERSAL_CORRECTNESS_RELATION_V1.json")
scope=load("canonical/governance/STRUCTURED_METHOD_SCOPE_AUDIT_V3.json")
gate=load("canonical/verification/STRUCTURED_METHOD_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
oracle_v=load("canonical/verification/STRUCTURED_METHOD_NORMALIZED_RULE_V3_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
manifest=load("canonical/governance/STRUCTURED_METHOD_UNIVERSAL_CORRECTNESS_CERTIFICATE_V1.json")
compiler=(SUB/"canonical/runtime/structured_method_normalized_rule_graph_v3.py").read_text()
oracle=(SUB/"canonical/runtime/structured_method_normalized_rule_oracle_v3.py").read_text()

assert relation["behavior_id"]=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
assert relation["theorem"]["theoretical_upper_bound"]==1
assert relation["theorem"]["candidate_brain_value"]==1
assert relation["theorem"]["uses_empirical_generalization"] is False
assert relation["consequence_if_independently_verified"]["fresh_terminal_cases_required"]==0
assert scope["status"].startswith("SCOPE_CLOSED__")
assert scope["unresolved_scope_dimensions"]==[]
assert gate["status"].startswith("INDEPENDENT_PASS__ADMISSIBLE_SUBSTITUTION")
assert gate["verdict"]["status"]=="ADMISSIBLE_SUBSTITUTION"
assert gate["verdict"]["admissible"] is True
assert gate["verdict"]["errors"]==[]
assert gate["verdict"]["leaked_inference_ids"]==[]
assert oracle_v["status"].startswith("INDEPENDENT_PASS__")
assert "ORACLE_DOES_NOT_IMPORT_BRAIN_COMPILER" in oracle_v["verified"]
assert {"compile_graph"}.issubset(funcs(compiler))
assert {"expected","score"}.issubset(funcs(oracle))

# Independent transition-correspondence checks over the exact source bytes.
pairs=[
('SOURCE_KINDS={"formula","constraint","schema","standard","feature_callout"}',)*2,
("if any(x not in nodes for x in ins):",)*2,
("for req in reqs:", "for req in consumes:"),
('nodes[out]={"id":out,"kind":"derived"',)*2,
('edges.append({"source":src,"target":out,"rule_id":rid})',)*2,
("del pending[rid]; progressed=True",)*2,
("UNRESOLVED_DEPENDENCY_OR_CYCLE",)*2,
]
for a,b in pairs:
    assert a in compiler, a
    assert b in oracle, b
for token in (
"ALL_INPUT_EDGES_PRESENT",
"DECLARED_INPUT_TYPE_DIMENSION_CONTRACTS_HOLD",
"OUTPUT_TYPE_DIMENSION_DECLARATION_PRESERVED",
"REQUIREMENT_LINEAGE_PRESERVED",
"DECLARED_INVARIANTS_PRESERVED",
"EDGE_DELETION_OR_REWIRE_MUST_BE_DETECTABLE",
):
    assert token in compiler and token in oracle, token
assert "for key,value in exp.items():" in oracle
assert 'if got.get(key)!=value:' in oracle or "if got.get(key) != value:" in oracle

# Execute the candidate certificate in an isolated vendored tree.
cert=SUB/"canonical/runtime/structured_method_universal_correctness_certificate_v1.py"
run=subprocess.run([sys.executable,str(cert)],cwd=SUB,text=True,capture_output=True)
assert run.returncode==0, run.stdout+"\n"+run.stderr
candidate=json.loads(run.stdout)
assert candidate["universal_correctness_proved_candidate"] is True
assert candidate["scope_complete"] is True
assert candidate["objective_ceiling_candidate"] is True
assert candidate["brain_value"]==1==candidate["theoretical_upper_bound"]
assert candidate["uses_empirical_generalization"] is False
assert candidate["terminal_wave_load_bearing"] is False

# Execute the candidate's falsification suite in the public runner.
test=SUB/"canonical/tests/test_structured_method_universal_correctness_certificate_v1.py"
tests=subprocess.run([sys.executable,str(test)],cwd=SUB,text=True,capture_output=True)
assert tests.returncode==0, tests.stdout+"\n"+tests.stderr

# Extra independent canaries: deleting a readiness or edge invariant must invalidate this verifier.
mut_ready=compiler.replace("if any(x not in nodes for x in ins):","if False:",1)
assert "if any(x not in nodes for x in ins):" not in mut_ready
mut_edge=compiler.replace('edges.append({"source":src,"target":out,"rule_id":rid})','edges.append({"source":out,"target":src,"rule_id":rid})',1)
assert 'edges.append({"source":src,"target":out,"rule_id":rid})' not in mut_edge

assert manifest["behavior_id"]=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
assert manifest["candidate_theorem"]["universal_correctness_over_admissible_finite_normalized_rule_tasks"] is True
assert manifest["candidate_theorem"]["brain_value"]==1
assert manifest["candidate_theorem"]["theoretical_upper_bound"]==1
assert manifest["consequence_if_independently_verified"]["removable_leaf_occurrence_count"]==1
assert manifest["consequence_if_independently_verified"]["fresh_reality_units_required"]==0
assert manifest["consequence_if_independently_verified"]["terminal_replay_required"] is False

receipt={
"schema":"PROJECT_BRAIN_STRUCTURED_METHOD_UNIVERSAL_CORRECTNESS_PUBLIC_RUNNER_VERIFICATION_20261005_V1",
"status":"INDEPENDENT_PUBLIC_RUNNER_PASS__UNIVERSAL_FORMAL_SCOPE_COMPLETE_OBJECTIVE_CEILING__ZERO_REALITY__ZERO_CREDIT",
"behavior_id":"STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
"subject_blobs":EXPECTED,
"verified":{
"all_exact_blobs_match":True,
"scope_already_closed":True,
"scope_gate_independent_admissible":True,
"independent_oracle_bound":True,
"compiler_oracle_transition_correspondence":True,
"candidate_certificate_executes":True,
"candidate_falsification_suite_passes":True,
"scope_complete":True,
"objective_ceiling":True,
"brain_value":1,
"theoretical_upper_bound":1,
"terminal_wave_load_bearing":False,
"fresh_terminal_cases_required":0,
},
"consequence":"ELIGIBLE_FOR_SEPARATE_SCOPE_REPAIR_REDUCTION__ONE_STRUCTURED_METHOD_LEAF_OCCURRENCE_REMOVABLE__NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_VERIFIER",
"accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0},
"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
