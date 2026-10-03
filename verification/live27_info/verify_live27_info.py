#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BLOBS={
"canonical/runtime/current_terminal_scheduling_world_v2.py":"1b09388b91ba52e1f13e3e26af9f97f8dd2eca65",
"canonical/runtime/current_terminal_information_dominance_v2.py":"f5a91705684df50d50e0126a0d871b02ead6f8d4",
"canonical/tests/test_current_terminal_information_dominance_v2.py":"a1585a0f09b3216294f4466712c2cfc3fad5dca7",
"canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V2.json":"229a9b0814cb330eff446111d5e41183c0601632",
"canonical/governance/CURRENT_TERMINAL_INFORMATION_DOMINANCE_V2.json":"aa8ebb7ceec9b257b0177e86f5a77d81e7eecc82",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json":"4b5517dbd12978f8ffe481fb775e85592c7790c8",
"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json":"ec0ca144939a19234f1c53378cc76af2014a6179",
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"2560dbf990a4f39f006884a2c0d1fa7950e15795",
}
def local(path):
    return ROOT/path.replace("/","__")
def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def raw(path):
    data=local(path).read_bytes()
    assert blob(data)==BLOBS[path],(path,blob(data),BLOBS[path])
    return data
def load(path):
    return json.loads(raw(path).decode("utf-8"))

for p in BLOBS:
    raw(p)

registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
frontier=load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
hyper=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
world=load("canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V2.json")
info=load("canonical/governance/CURRENT_TERMINAL_INFORMATION_DOMINANCE_V2.json")

ids=[x["id"] for x in registry["predicates"]]
assert len(ids)==38 and len(set(ids))==38
states={x["predicate_id"]:x["state"] for x in evidence["claims"]}
proved={x for x,s in states.items() if s=="PROVED"}
refuted={x for x,s in states.items() if s=="REFUTED"}
terminal=proved|refuted
unresolved=[x for x in ids if x not in terminal]
U=set(unresolved)
assert len(proved)==11,(len(proved),sorted(proved))
assert len(refuted)==0
assert len(unresolved)==27
assert authority["truth"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert authority["atomic_acceptance_frontier"]["proved"]==11
assert authority["atomic_acceptance_frontier"]["unresolved"]==27
assert authority["atomic_acceptance_frontier"]["total"]==38

certs=[]
for c in frontier["certificates"]:
    keep=[x for x in c["target_predicates"] if x in U]
    if keep:
        certs.append({
            "id":c["id"],
            "targets":set(keep),
            "requires":set(c.get("requires",[])),
            "reality":float(c.get("new_reality_units",0)),
        })
actions=[]
for a in hyper["actions"]:
    keep=[x for x in a.get("target_predicates",[]) if x in U]
    if keep:
        actions.append((a["id"],set(keep)))
covered=set().union(*(x[1] for x in actions))
assert len(certs)==16
assert len(actions)==21
assert covered==U,(sorted(U-covered),sorted(covered-U))

def subset(a,b): return a <= b
def dominates(a,b):
    return (
        a["targets"] >= b["targets"]
        and a["requires"] <= b["requires"]
        and a["reality"] <= b["reality"]
        and (
            a["targets"] > b["targets"]
            or a["requires"] < b["requires"]
            or a["reality"] < b["reality"]
        )
    )
dominated={}
for b in certs:
    ds=sorted(a["id"] for a in certs if a["id"]!=b["id"] and dominates(a,b))
    if ds: dominated[b["id"]]=ds
assert dominated=={},dominated
max_cov=max(len(c["targets"]) for c in certs)
max_ids=sorted(c["id"] for c in certs if len(c["targets"])==max_cov)
assert max_cov==8
assert max_ids==["MATCHED_SCOPE_BINDING_CERTIFICATE"]
matched=next(c for c in certs if c["id"]=="MATCHED_SCOPE_BINDING_CERTIFICATE")
for pid in (
    "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
    "RECOVERY_TERMINAL_NONINFERIOR",
    "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
):
    assert pid not in matched["targets"]

all_targets=set().union(*(c["targets"] for c in certs))
all_requirements=set().union(*(c["requires"] for c in certs))
assert all_targets==U
assert len(all_requirements)==19
assert all(c["reality"]==0 for c in certs)

ew=world["expected_live_world"]
assert ew["registry_predicates"]==38
assert ew["proved_predicates"]==11
assert ew["unresolved_predicates"]==27
assert ew["live_certificates"]==16
assert ew["live_actions"]==21
assert ew["live_action_coverage"]==27
assert ew["uncovered_predicates"]==0
assert world["exact_inputs"]["current_terminal_authority"]["git_blob_sha"]==BLOBS["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]
assert world["exact_inputs"]["predicate_registry"]["git_blob_sha"]==BLOBS["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"]
assert world["exact_inputs"]["evidence_bindings"]["git_blob_sha"]==BLOBS["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"]
assert world["exact_inputs"]["historical_frontier"]["git_blob_sha"]==BLOBS["canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"]
assert world["exact_inputs"]["historical_action_hypergraph"]["git_blob_sha"]==BLOBS["canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"]

er=info["expected_result"]
assert er["unresolved_predicates"]==27
assert er["certificate_count"]==16
assert er["nondominated_certificate_count"]==16
assert er["dominated_certificate_count"]==0
assert er["live_action_count"]==21
assert er["live_action_coverage_count"]==27
assert er["unique_zero_reality_requirements"]==19
assert er["highest_direct_coverage"]["certificate_id"]=="MATCHED_SCOPE_BINDING_CERTIFICATE"
assert er["highest_direct_coverage"]["covered_predicates"]==8
assert abs(er["highest_direct_coverage"]["fraction_of_live_atomic_frontier"]-(8/27))<1e-15
assert er["full_frontier_new_reality_units"]==0

sched_src=raw("canonical/runtime/current_terminal_scheduling_world_v2.py").decode("utf-8")
info_src=raw("canonical/runtime/current_terminal_information_dominance_v2.py").decode("utf-8")
assert "PROVED_COUNT_NOT_8" not in sched_src
assert "UNRESOLVED_COUNT_NOT_30" not in sched_src
assert "3/19_PASS__16/19_OPEN" not in sched_src
assert "AUTHORITY_ATOMIC_FRONTIER_NOT_OBJECT" in sched_src
assert "current_terminal_scheduling_world_v2" in info_src

print("LIVE27_INFORMATION_DOMINANCE_INDEPENDENT_PASS")
print(json.dumps({
    "brain_head":"1bef0cde547d36582aa7570b8fdb8684a1e6eb32",
    "unresolved":len(unresolved),
    "certificates":len(certs),
    "actions":len(actions),
    "coverage":len(covered),
    "dominated":len(dominated),
    "unique_requirements":len(all_requirements),
    "max_direct_coverage":max_cov,
    "max_direct_certificate":max_ids,
    "fresh_reality_authority":False,
},sort_keys=True))
