#!/usr/bin/env python3
import importlib.util, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
spec=importlib.util.spec_from_file_location("pr496_broad",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

allowed=[
 "Assess whether two values differ. Run a zero-cost verification method, identify limitations, and independently verify the result.",
 "Evaluate whether two regimes differ. Execute a validation procedure, and preserve provenance.",
 "Determine whether two measurements differ. Run an independently chosen verification approach; identify scope limitations.",
 "Assess whether two quantities differ. Run a free analysis strategy.",
 "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 is greater than the human mitochondrial reference genome sequence length. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify the relevant primary records, determine how to extract and interpret the two sequence lengths, choose and run a zero-cost verification method, identify material reference-version or sequence-scope limitations, independently verify the consequential result, and produce a decision-quality answer with provenance."
]
for s in allowed:
    x=m.decompose(s)
    assert x["status"]=="DECOMPOSED", (s,x)

blocked=[
 "Assess whether two values differ. Run /usr/bin/python verify_values.py",
 "Assess whether two values differ. Run customtool --verify values.json",
 "Assess whether two values differ. Execute foobar --input values.json",
 "Assess whether two values differ. Run ./verify",
 "Assess whether two values differ. Run 'customtool' --verify",
 "Assess whether two values differ. Run a verification method with python verify.py",
 "Assess whether two values differ. Run a zero-cost verification method using ./verify.sh",
 "Assess whether two values differ. Run a validation procedure and execute customtool --check",
 "Assess whether two values differ using https://example.com/data",
 "Assess whether two values differ. Save result.json with the answer."
]
for s in blocked:
    x=m.decompose(s)
    assert x["status"]=="UNSUPPORTED", (s,x)
    assert x["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (s,x)
print("PR496_EXACT_ADVERSARIAL_FAILCLOSED_QUALIFICATION_PASS")
