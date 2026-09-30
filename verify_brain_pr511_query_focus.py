#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parent
PATH=ROOT/"canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py"
spec=importlib.util.spec_from_file_location("pr511_query_focus_candidate",PATH)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)

fail=[]; cases=[]
def check(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond: fail.append(label)

fresh=[
 (
  "Assess whether RFC 9110 obsoletes RFC 7230. Use authoritative primary technical evidence, choose and run a zero-cost verification method, independently verify the consequential result, and preserve provenance.",
  ("RFC 9110","RFC 7230")
 ),
 (
  "Determine whether Python 3.13 supports a free-threaded build mode. Use authoritative technical evidence, choose a verification method, identify material limitations, independently verify the result, and preserve provenance.",
  ("Python 3.13","free-threaded")
 )
]
for i,(objective,needles) in enumerate(fresh):
    q=mod._query(objective)
    check(f"fresh_{i}_wrapper_removed",not q.lower().startswith(("assess ","determine ")),q)
    check(f"fresh_{i}_instructions_removed","authoritative" not in q.lower() and "verification method" not in q.lower(),q)
    for j,n in enumerate(needles):
        check(f"fresh_{i}_entity_{j}_preserved",n.lower() in q.lower(),q)
    out=mod.discover(objective,limit=12,timeout=20)
    check(f"fresh_{i}_live_discovery",out.get("status")=="CANDIDATES_DISCOVERED" and int(out.get("candidate_count") or 0)>0,out)
    check(f"fresh_{i}_query_bound",out.get("query")==q,{"query":out.get("query"),"expected":q})
    hay="\n".join(
      " ".join(str(c.get(k) or "") for k in ("url","title","snippet")).lower()
      for c in (out.get("candidates") or [])
    )
    check(f"fresh_{i}_decision_terms_reached_live_candidates",
          any(n.lower() in hay for n in needles),{"query":q,"candidates":out.get("candidates")})

explicit="RFC 9110 HTTP semantics official specification"
check("explicit_preserved",mod._query(explicit)==explicit,mod._query(explicit))

adversarial=[
 "Use authoritative evidence to assess a standard",
 "Please assess whether two values differ",
 "Summarize a report about assess vocabulary",
]
for i,x in enumerate(adversarial):
    q=mod._query(x)
    if x.lower().startswith("assess whether"):
        pass
    else:
        check(f"adversarial_{i}_unrecognized_prefix_preserved",q==x,q)

report={
 "schema":"BRAIN_PR511_QUERY_FOCUS_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS" if not fail else "FAIL",
 "brain_pr":511,
 "candidate_runtime_blob":"a3ae22718c82569fdc954f979cb347189d6edfcd",
 "candidate_test_blob":"d93e1c3a4b689884a10c474d049bd1e4aad830a2",
 "failures":fail,
 "cases":cases,
 "model_dependency_count":0,
 "incremental_spend_usd":0,
 "parent_task_executed":False
}
(ROOT/"pr511-independent-query-focus-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
