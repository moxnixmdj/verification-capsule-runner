#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
spec=importlib.util.spec_from_file_location("pr496_broad",P)
mod=importlib.util.module_from_spec(spec); sys.modules["pr496_broad"]=mod; spec.loader.exec_module(mod)

def expect(status,text):
    out=mod.decompose(text)
    assert out["status"]==status,(status,text,out)
    return out

allowed=[
    "Assess whether two measurements differ. Run a verification method.",
    "Evaluate whether two regimes differ. Execute a validation procedure, and independently verify the result.",
    "Investigate whether two values differ. Run an independently chosen verification approach; preserve material limitations.",
    "Assess whether two values differ. Choose and run a zero-cost verification method, identify limitations, and preserve provenance.",
    "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 is greater than the human mitochondrial reference genome sequence length. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify the relevant primary records, determine how to extract and interpret the two sequence lengths, choose and run a zero-cost verification method, identify material reference-version or sequence-scope limitations, independently verify the consequential result, and produce a decision-quality answer with provenance.",
]
for x in allowed:
    out=expect("DECOMPOSED",x)
    assert out["model_dependency_count"]==0
    assert out["invented_source_urls"]==[]

rejected=[
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Run customtool --verify values.json",
    "Assess whether two values differ. Execute ./verify.sh",
    r"Assess whether two values differ. Run C:\Tools\verify.exe --check",
    "Assess whether two values differ. Run python verify_values.py",
    "Assess whether two values differ. Run a verification method with python verify.py",
    "Assess whether two values differ. Execute an analysis strategy using curl https://example.com/x",
    "Assess whether two values differ. Run a free verification method and save result.json",
    "Assess whether two values differ using https://example.com/data",
]
for x in rejected:
    out=expect("UNSUPPORTED",x)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",(x,out)

print("PR496_EXACT_ADVERSARIAL_QUALIFICATION_PASS")
