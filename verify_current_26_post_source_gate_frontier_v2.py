#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subjects/current_26_post_source_gate_v2"

EXPECTED={
 "candidate_runtime":"99bb7d41547f15ed563a5d52a572fd3972880431",
 "candidate_test":"538451d68cff200319605c59d470db03e38c83fc",
 "candidate_gov":"18a4e14151971d3743e1425ac4baf45f0b5b32c9",
 "registry":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "evidence":"f99b00e6dca735ffa7a790a414155b4f69856cf0",
 "old_frontier":"bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
 "cert_frontier":"4b5517dbd12978f8ffe481fb775e85592c7790c8",
 "matched":"438e2775b64bee5ed6e792522ab35ebd0d6e1771",
 "tdver":"bed23f2e69d4bc8937d792b07b5812364cf26a85",
 "source_act":"4211a0eee07c4758035d788c0be897d700c164cb",
 "source_ver":"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
}
FILES={
 "candidate_runtime":"candidate_runtime.py",
 "candidate_test":"candidate_test.py",
 "candidate_gov":"candidate_gov.json",
 "registry":"registry.json",
 "evidence":"evidence.json",
 "old_frontier":"old_frontier.json",
 "cert_frontier":"cert_frontier.json",
 "matched":"matched.json",
 "tdver":"tdver.json",
 "source_act":"source_act.json",
 "source_ver":"source_ver.json",
}
DISCHARGED={
 "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
 "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}
DIRECT={
 "FINANCE_UNCOVERED_SCOPE_AUDIT",
 "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
}
MATCHED_PARENT={
 "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
 "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}

def blob(path):
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(key):
 return json.loads((SUB/FILES[key]).read_text(encoding="utf-8"))

for key,name in FILES.items():
 actual=blob(SUB/name)
 assert actual==EXPECTED[key],(key,actual,EXPECTED[key])

reg=load("registry"); evid=load("evidence"); old=load("old_frontier")
cert=load("cert_frontier"); matched=load("matched"); tdver=load("tdver")
act=load("source_act"); sver=load("source_ver"); gov=load("candidate_gov")

claims=evid.get("claims") or []
proved={x.get("predicate_id") for x in claims if isinstance(x,dict) and x.get("state")=="PROVED"}
predicates=[x.get("id") for x in reg.get("predicates",[]) if isinstance(x,dict) and isinstance(x.get("id"),str)]
unresolved=set(predicates)-proved
assert (len(predicates),len(proved),len(unresolved))==(38,12,26)
assert "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in proved
assert str(tdver.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")

assert str(sver.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
sv=sver["verified"]
assert set(sv["discharged_requirements"])==DISCHARGED
assert sv["finance_source_admitted"] is True
assert sv["unknown_domain_source_admitted"] is True
assert sv["direct_oracle_leaves_executed"] is False
assert sv["global_fresh_reality_authority"] is False
assert set(act["discharged_requirements"])==DISCHARGED
state=act["resulting_direct_protocol_state"]
assert state["clean_direct_case_execution_eligible"] is True
assert state["global_fresh_reality_authority"] is False

old_ids=set(old.get("active_nondominated_certificate_ids") or [])
rows=[]
for row in cert.get("certificates") or []:
 if not isinstance(row,dict): continue
 if row.get("id") not in old_ids: continue
 targets={t for t in row.get("target_predicates",[]) if isinstance(t,str) and t in unresolved}
 if targets:
  rows.append((row,targets))

assert all(row.get("id")!="TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" for row,_ in rows)
raw_req={r for row,_ in rows for r in row.get("requires",[]) if isinstance(r,str)}
assert DISCHARGED.issubset(raw_req)

zero=[]; direct=[]
for row,targets in rows:
 remaining={r for r in row.get("requires",[]) if isinstance(r,str)}-DISCHARGED
 if remaining:
  zero.append((row,targets,remaining))
 elif targets.issubset(DIRECT):
  direct.append((row,targets))
 else:
  raise AssertionError(("unresolved certificate lost requirements",row.get("id"),targets))

zero_ids={row.get("id") for row,_,_ in zero}
zero_req={r for _,_,reqs in zero for r in reqs}
zero_targets={t for _,targets,_ in zero for t in targets}
direct_targets={t for _,targets in direct for t in targets}
assert len(zero_ids)==11
assert len(zero_req)==14
assert len(zero_targets)==22
assert len(direct)==2
assert direct_targets==DIRECT
assert DISCHARGED.isdisjoint(zero_req)

imp=[x for x in matched.get("implications",[]) if isinstance(x,dict)]
child={
 f for edge in imp
 if edge.get("verified") is True and edge.get("independent") is True
 for f in edge.get("if_all",[]) if isinstance(f,str)
}
matched_targets={t for edge in imp for t in edge.get("then",[]) if isinstance(t,str)}
assert len(child)==16
assert len(matched_targets)==8
assert MATCHED_PARENT.issubset(zero_req)
primitive=len(zero_req)-len(MATCHED_PARENT)+len(child)
assert primitive==28

x=gov["exact_reconciliation"]
assert x["acceptance"]=="5/19_PASS__14/19_OPEN"
assert x["atomic"]=="12_PROVED__26_UNRESOLVED"
assert set(x["discharged_zero_reality_requirements"])==DISCHARGED
assert x["active_zero_reality_requirements"]==14
assert x["active_zero_reality_certificates"]==11
assert x["zero_reality_covered_predicates"]==22
assert x["primitive_zero_reality_work_units"]==28
assert x["matched_priority_child_facts"]==16
assert set(x["direct_reality_eligible_predicates"])==DIRECT
assert x["direct_reality_execution_authorized_now"] is False
assert x["global_fresh_reality_authority"] is False
assert gov["acceptance_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["ownership_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False

print("CURRENT_26_POST_SOURCE_GATE_FRONTIER_V2_INDEPENDENT_VERIFIED")
