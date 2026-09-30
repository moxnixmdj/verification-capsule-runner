#!/usr/bin/env python3
import importlib.util,json,pathlib,shutil,sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
MOD=ROOT/"qualification"/"generic_source_discovery_v1.py"
REPORT=ROOT/"generic-source-discovery-qualification.json"

spec=importlib.util.spec_from_file_location("generic_source_discovery_v1",MOD)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

fixtures=[
 {"id":"PYTHON_PATHLIB","objective":"Determine whether Python 3 pathlib Path read_text accepts an encoding argument.","expected":"docs.python.org"},
 {"id":"GIT_SWITCH","objective":"Determine whether git switch provides a discard-changes option.","expected":"git-scm.com"},
 {"id":"SI_LIGHT_SPEED","objective":"Determine the exact SI defining value of the speed of light in vacuum.","expected":"bipm.org"},
]
oracle={"id":"POSTGRES_PGDUMP","objective":"Determine whether PostgreSQL pg_dump can make internally consistent exports while the database is being used concurrently.","expected":"postgresql.org"}

src=MOD.read_text(encoding="utf-8").lower()
for f in fixtures+[oracle]:
    assert f["expected"] not in src,"TASK_SPECIFIC_AUTHORITY_DOMAIN_LEAK"
assert shutil.which("ddgr"),"DDGR_NOT_INSTALLED"

def run(f):
    result=mod.discover(f["objective"])
    cs=result.get("candidates") or []
    matches=[c for c in cs if c.get("host","").lower().endswith(f["expected"])]
    bindings=[mod.verify_url_binding(c["url"]) for c in matches[:2]]
    bound=[b for b in bindings if b.get("status")=="BOUND" and (b.get("http_status") or 0)<400]
    return {
      "fixture":f,"candidate_count":len(cs),"expected_domain_match_count":len(matches),
      "expected_domain_examples":matches[:3],"bindings":bindings,
      "passed":bool(matches and bound),
      "model_dependency_count":result.get("model_dependency_count"),
      "authority_claimed":result.get("authority_claimed"),
      "observations":result.get("observations"),
    }

authored=[run(f) for f in fixtures]
fresh=run(oracle)
checks={
 "ddgr_installed":bool(shutil.which("ddgr")),
 "task_specific_domain_leak_absent":True,
 "authored_cross_domain_pass_count":sum(1 for x in authored if x["passed"]),
 "authored_cross_domain_total":len(authored),
 "fresh_oracle_passed":fresh["passed"],
 "all_model_dependency_zero":all(x["model_dependency_count"]==0 for x in authored+[fresh]),
 "candidate_never_claims_authority":all(x["authority_claimed"] is False for x in authored+[fresh]),
}
passed=(checks["authored_cross_domain_pass_count"]==checks["authored_cross_domain_total"] and checks["fresh_oracle_passed"] and checks["all_model_dependency_zero"] and checks["candidate_never_claims_authority"])
report={
 "schema":"PROJECT_BRAIN_GENERIC_SOURCE_DISCOVERY_QUALIFICATION_V1",
 "status":"PASS" if passed else "FAIL",
 "capability_scope":"MODEL_INDEPENDENT_PLAIN_GOAL_TO_SOURCE_CANDIDATE_DISCOVERY_AND_VERIFIED_URL_BINDING_V1",
 "claim_limit":"Does not certify source authority. It proves cross-domain retrieval of known authoritative candidates plus actual URL binding; authority adjudication remains separate.",
 "incremental_spend_usd":0,"model_dependency_count":0,"checks":checks,
 "authored_fixtures":authored,"independent_fresh_oracle":fresh,
 "next_if_pass":"QUALIFY_GENERIC_AUTHORITY_ADJUDICATION_OVER_DISCOVERED_CANDIDATES__THEN_COMPOSE_WITH_EXISTING_FETCH_EXTRACTION_NUMERIC_SYNTHESIS_VERIFICATION",
 "next_if_fail":"PRESERVE_FIRST_DISCOVERY_OR_BINDING_CAUSAL_GAP__DO_NOT_SPEND_PARENT_TASK",
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if passed else 2)
