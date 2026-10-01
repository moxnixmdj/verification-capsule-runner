import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from requirement_graph_kernel import compile_requirement_contract, requirement_mutation_score
from independent_acceptance_model import assess

root=Path(__file__).parent
c=json.loads((root/"contract.json").read_text())
s=json.loads((root/"source_accounting.json").read_text())
reqs=c["normalized_requirements"]
expected=c["expected_required_ids"]
checks=c["independent_acceptance"]["oracles"]

graph=compile_requirement_contract(reqs,expected_required_ids=expected)
if not graph["pass"]:
    raise SystemExit("requirement graph failed: "+json.dumps(graph["graph"]["diagnostics"]))

mut=requirement_mutation_score(reqs)
if not mut["pass"]:
    raise SystemExit("requirement mutation survivors: "+json.dumps(mut["survived_ids"]))

accept=assess({"requirements":reqs,"checks":checks})
if not accept["pass"]:
    failed={x["requirement_id"]:x["uncovered"] for x in accept["requirements"] if not x["pass_independent_acceptance"]}
    raise SystemExit("independent acceptance uncovered: "+json.dumps(failed,sort_keys=True))

if len(reqs)!=len(set(expected)) or set(expected)!={r["id"] for r in reqs}:
    raise SystemExit("requirement identity mismatch")
if c.get("v3_metrics",{}).get("requirements") != len(reqs):
    raise SystemExit("V3 metric requirement count mismatch")
if len(checks)!=len(reqs):
    raise SystemExit("must have exactly one independent oracle per requirement")

source_ids={x["id"] for x in s.get("sources",[])}
mutants=set(c.get("verifier_mutants",[]))
for r in reqs:
    if r.get("open_questions"):
        raise SystemExit("open question in "+r["id"])
    refs=r.get("source_refs",[])
    if not refs:
        raise SystemExit("untraced requirement "+r["id"])
    unknown=set(refs)-source_ids
    if unknown:
        raise SystemExit("unknown source ref "+r["id"]+" "+json.dumps(sorted(unknown)))
    modes=set(r.get("must_detect_failure_modes",[]))
    oracle=[x for x in checks if x.get("covers")==[r["id"]]]
    if len(oracle)!=1:
        raise SystemExit("oracle count mismatch "+r["id"])
    detects=set(oracle[0].get("detects",[]))
    if not modes.issubset(detects):
        raise SystemExit("oracle misses explicit mode "+r["id"])
    for mode in detects:
        mid="M_"+r["id"]+"__"+mode.upper()
        if mid not in mutants:
            raise SystemExit("declared acceptance mode lacks named mutant "+mid)

if c.get("task_execution_authorized") is not False:
    raise SystemExit("contract illegally authorizes execution")
boundary=c["source_boundary"]
for k in ("solution_read","tests_read","hidden_verifier_read","task_specific_repository_search_after_exposure","task_specific_external_search","task_command_executed"):
    if boundary.get(k) is not False:
        raise SystemExit("source boundary violation "+k)
for k in ("solution_read","tests_read","hidden_verifier_read","task_specific_external_search","task_command_executed"):
    if s.get(k) is not False:
        raise SystemExit("source accounting violation "+k)
if s.get("forbidden_sources_read"):
    raise SystemExit("forbidden reads recorded")

print(json.dumps({
  "pass":True,
  "requirements":len(reqs),
  "source_traced_requirements":sum(bool(r.get("source_refs")) for r in reqs),
  "structural_mutants":mut["total"],
  "structural_mutants_killed":mut["killed"],
  "declared_behavioral_mutants":len(mutants),
  "independent_acceptance_requirements":len(accept["requirements"]),
  "source_boundary":"PASS"
},sort_keys=True))
