#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
PATH=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
spec=importlib.util.spec_from_file_location("qualified_broad_objective_decompose",PATH)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

def status(text):
    return mod.decompose(text)

genomics=(
    "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 "
    "is greater than the human mitochondrial reference genome sequence length. Use authoritative "
    "primary technical evidence and a real executable check. Autonomously discover and verify the "
    "relevant primary records, determine how to extract and interpret the two sequence lengths, "
    "choose and run a zero-cost verification method, identify material reference-version or "
    "sequence-scope limitations, independently verify the consequential result, and produce a "
    "decision-quality answer with provenance."
)
g=status(genomics)
assert g["status"]=="DECOMPOSED", g

legitimate=[
    "Assess whether two measured values differ. Execute a validation procedure, and independently verify the result.",
    "Evaluate whether two operating regimes differ. Run an independently chosen verification approach; preserve material limitations.",
    "Determine whether two documented limits differ. Choose and run a zero-cost verification method, then independently verify the result.",
]
for text in legitimate:
    out=status(text)
    assert out["status"]=="DECOMPOSED", (text,out)

recipes=[
    "Assess whether two measured values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two measured values differ. Run customtool --verify values.json",
    "Assess whether two measured values differ. Execute /opt/local/bin/checker input.txt",
    "Assess whether two measured values differ. Run python verify.py",
    "Assess whether two measured values differ. Run a verification method with python verify.py",
    "Assess whether two measured values differ using https://example.com/data.json",
]
for text in recipes:
    out=status(text)
    assert out["status"]=="UNSUPPORTED", (text,out)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (text,out)

print("INDEPENDENT_PR496_EXPLICIT_RECIPE_FAILCLOSED_PASS")
