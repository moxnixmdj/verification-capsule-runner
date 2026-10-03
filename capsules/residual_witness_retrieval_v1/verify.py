#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import pathlib
import py_compile

ROOT=pathlib.Path(__file__).resolve().parent

def load(name,filename):
    path=ROOT/filename
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+filename)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

for name in (
    "residual_witness_retrieval_compiler_v1.py",
    "research_query_focus.py",
    "objective_relevance_bm25.py",
    "objective_claim_operand_binding.py",
):
    py_compile.compile(str(ROOT/name),doraise=True)

r=load("retrieval","residual_witness_retrieval_compiler_v1.py")
focus=load("focus","research_query_focus.py")
rank=load("rank","objective_relevance_bm25.py")

objective="比较 中文 编解码器 与 العربية ترميز و кодек formats"
f=focus.focus(objective)
assert f["status"]=="FOCUSED",f
for token in ("中文","编解码器","العربية","ترميز","кодек"):
    assert token in f["query"],(token,f)

ranked=rank.rank(
    "中文 编解码器 UBJSON",
    [
        {"url":"https://wrong.example","title":"unrelated serializer","snippet":"english only"},
        {"url":"https://right.example","title":"中文 UBJSON 编解码器","snippet":"二进制 编码"},
    ],
)
assert ranked["status"]=="LEXICAL_RELEVANCE_RANKED",ranked
assert ranked["top_candidate_original_index"]==1,ranked

residual={
    "residual_id":"R-CODEC-UBJSON",
    "effect":"Encode structured records as UBJSON without network-dependent runtime cost",
    "required_capabilities":["structured.binary.encode.ubjson"],
    "aliases":["Universal Binary JSON","UBJSON codec"],
    "language_variants":{
        "zh":["通用二进制 JSON 编码","UBJSON 编解码器"],
        "ar":["ترميز UBJSON","مُرمِّز UBJSON"],
    },
    "observables":{
        "api_symbols":["dumpb","loadb"],
        "file_formats":["ubj","ubjson"],
        "commands":["ubjson"],
        "imports":["ubjson"],
    },
    "constraints":{"incremental_spend_usd":0},
}
program=r.compile_residual(residual)
texts=[x["text"] for x in program["query_lattice"]]
for required in ("通用二进制 JSON 编码","ترميز UBJSON","dumpb","loadb"):
    assert required in texts,(required,texts)
state=r.initial_state(program)
assert r.terminal_status(state)["status"]=="UNKNOWN_CONTINUE_RETRIEVAL"

for cell in list(state["cells"]):
    state=r.update_cell(
        state,
        query_id=cell["query_id"],
        surface=cell["surface"],
        cell_state="QUERIED_NO_CANDIDATE",
    )
terminal=r.terminal_status(state)
assert terminal["status"]=="UNKNOWN_CONTINUE_RETRIEVAL",terminal
assert terminal["nonexistence_claim_authorized"] is False,terminal
assert r.next_action(program,state)["reason"]=="NO_QUERYABLE_CELL_BUT_SCOPE_NOT_PROVEN_COMPLETE"

state=r.initial_state(program)
for surface in ("REPOSITORY_METADATA","SOCIAL_TECHNICAL_DISCUSSION"):
    try:
        r.add_verified_witness(
            state,
            witness_id="candidate-only",
            residual_id=program["residual_id"],
            source_surface=surface,
            independent_receipt="receipt://invalid",
        )
    except ValueError as exc:
        assert "CANDIDATE_ONLY_SURFACE_CANNOT_VERIFY" in str(exc),exc
    else:
        raise AssertionError("candidate-only surface self-verified: "+surface)

state=r.add_verified_witness(
    state,
    witness_id="repo@sha:contract",
    residual_id=program["residual_id"],
    source_surface="CODE_CONTENT",
    independent_receipt="receipt://independent/1",
)
terminal=r.terminal_status(state)
assert terminal["status"]=="VERIFIED_WITNESS_FOUND",terminal
assert terminal["stop"] is True,terminal

first_state=r.initial_state(program)
first=r.next_action(program,first_state)
first_state=r.update_cell(
    first_state,
    query_id=first["query_id"],
    surface=first["surface"],
    cell_state="QUERIED_NO_CANDIDATE",
)
second=r.next_action(program,first_state)
assert first["surface"]!=second["surface"],(first,second)

scoped=dict(residual)
scoped["declared_scope"]={
    "scope_id":"FROZEN-CODE-SYMBOL-SNAPSHOT",
    "independently_verified_complete":True,
    "required_surfaces":["CODE_CONTENT","SYMBOLS"],
    "required_query_ids":["Q000"],
}
p2=r.compile_residual(scoped)
s2=r.initial_state(p2)
for surface in ("CODE_CONTENT","SYMBOLS"):
    s2=r.update_cell(
        s2,
        query_id="Q000",
        surface=surface,
        cell_state="EXHAUSTIVELY_CLOSED",
        independently_complete=True,
    )
t2=r.terminal_status(s2)
assert t2["status"]=="DECLARED_SCOPE_EXHAUSTIVELY_CLOSED",t2
assert t2["scope_limited"] is True,t2

unseen=r.capture_recapture_unseen(10,5)
assert unseen["estimated_unseen"]==10.0,unseen
assert unseen["completeness_proof"] is False,unseen

print(json.dumps({
    "status":"PASS",
    "unicode_focus":True,
    "unicode_relevance":True,
    "no_result_nonexistence_firewall":True,
    "candidate_only_self_verification_blocked":True,
    "first_verified_witness_stop":True,
    "orthogonal_surface_diversification":True,
    "scope_limited_exhaustive_closure":True,
    "capture_recapture_not_completeness_proof":True,
},sort_keys=True))
