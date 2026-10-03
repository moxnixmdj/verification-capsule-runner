#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib
import py_compile
import sys

ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import residual_witness_backend_router_v1 as router
from canonical.runtime import residual_witness_retrieval_compiler_v1 as core

for p in (
    ROOT/"canonical/runtime/residual_witness_backend_router_v1.py",
    ROOT/"canonical/runtime/residual_witness_retrieval_compiler_v1.py",
):
    py_compile.compile(str(p),doraise=True)

residual={
    "residual_id":"R1",
    "effect":"Decode a binary telemetry envelope",
    "required_capabilities":["telemetry.decode"],
    "observables":{"api_symbols":["decode_frame"]},
}
program=core.compile_residual(residual)
state=core.initial_state(program)
q=program["query_lattice"][0]
action={
    "action":"QUERY",
    "query_id":q["query_id"],
    "query":q["text"],
    "basis":q["basis"],
    "language_hint":q["language_hint"],
    "surface":"CODE_CONTENT",
}

candidate=router.execute_action(
    program,state,action,
    lambda a:{
        "backend_id":"FAKE",
        "candidates":[{"repository":"example/repo","path":"codec.py"}],
        "complete":False,
    },
)
assert candidate["status"]=="BACKEND_EXECUTED",candidate
assert candidate["result"]["candidate_count"]==1,candidate
assert candidate["result"]["candidates"][0]["sufficiency_status"]=="UNVERIFIED",candidate
assert candidate["terminal"]["stop"] is False,candidate

fake_complete=router.execute_action(
    program,state,action,
    lambda a:{
        "backend_id":"FAKE_COMPLETE",
        "candidates":[],
        "complete":True,
        "independently_complete":False,
    },
)
assert fake_complete["result"]["completeness_admitted"] is False,fake_complete
assert fake_complete["terminal"]["status"]=="UNKNOWN_CONTINUE_RETRIEVAL",fake_complete

real_complete=router.execute_action(
    program,state,action,
    lambda a:{
        "backend_id":"FROZEN_COMPLETE",
        "candidates":[],
        "complete":True,
        "independently_complete":True,
        "completeness_receipt":"receipt://frozen/code/Q000",
    },
)
cell=[
    x for x in real_complete["state"]["cells"]
    if x["query_id"]=="Q000" and x["surface"]=="CODE_CONTENT"
][0]
assert cell["state"]=="EXHAUSTIVELY_CLOSED",cell
assert cell["independently_complete"] is True,cell

authority=router.execute_action(
    program,state,action,
    lambda a:{
        "backend_id":"BAD",
        "candidates":[{"repository":"x/y","verified_sufficient":True}],
    },
)
assert authority["status"]=="BACKEND_REJECTED_PERMANENT",authority
assert "BACKEND_CANDIDATE_SELF_VERIFICATION" in authority["error"],authority
cell=[
    x for x in authority["state"]["cells"]
    if x["query_id"]=="Q000" and x["surface"]=="CODE_CONTENT"
][0]
assert cell["state"]=="FAILED_PERMANENT",cell

def boom(a):
    raise TimeoutError("simulated")
transient=router.execute_action(program,state,action,boom)
assert transient["status"]=="BACKEND_FAILED_TRANSIENT",transient
cell=[
    x for x in transient["state"]["cells"]
    if x["query_id"]=="Q000" and x["surface"]=="CODE_CONTENT"
][0]
assert cell["state"]=="FAILED_TRANSIENT",cell

initial_action=core.next_action(program,state)
assert initial_action["surface"] not in router.default_providers(),initial_action
unbound=router.execute_next(program,state)
assert unbound["status"]=="BACKEND_UNBOUND",unbound
assert unbound["terminal"]["stop"] is False,unbound

verified=router.accept_independent_witness(
    state,
    witness_id="repo@sha",
    residual_id="R1",
    source_surface="CODE_CONTENT",
    independent_receipt="receipt://independent/pass",
)
terminal=core.terminal_status(verified)
assert terminal["status"]=="VERIFIED_WITNESS_FOUND",terminal
assert terminal["stop"] is True,terminal

bound=set(router.default_providers())
assert {"PACKAGE_REGISTRY","OPEN_WEB","DOCUMENTATION","SCHOLARLY"}.issubset(bound),bound

print(json.dumps({
    "status":"PASS",
    "candidate_sufficiency_firewall":True,
    "fake_completeness_rejected":True,
    "independent_completeness_receipt_admitted":True,
    "backend_self_verification_quarantined":True,
    "transient_failure_stays_unknown":True,
    "unbound_surface_stays_unknown":True,
    "independent_witness_receipt_required":True,
    "built_in_zero_cost_backends_bound":True,
},sort_keys=True))
