from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

GRAPH_PATH=Path("PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json")
CATALOG_PATH=Path("PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json")
EXPECTED_GRAPH_BLOB="affa5085b6927489fef530bc89d0256694a46bac"
EXPECTED_CATALOG_BLOB="a218ae63418ff525fcb0e4b3c9b884cc2be0fbbe"
PRIMITIVES={"CLAIM","OBLIGATION","ASSUMPTION","EVIDENCE","DEPENDENCY","DEFEATER","EFFECT","AUTHORITY","RESOURCE","MONITOR","EPOCH","TRANSITION"}
STATUSES={"SUPPORTED","OPEN","STALE","PROVEN_IRRELEVANT","REJECTED"}
LEAF_TYPES={"EVIDENCE","ASSUMPTION","EPOCH"}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_exact(path: Path, expected: str):
    data=path.read_bytes()
    got=git_blob_sha(data)
    assert got==expected,(path,got,expected)
    return json.loads(data)

def validate(graph, catalog):
    errors=[]
    roots=graph.get("root_ids")
    rows=graph.get("nodes")
    if not isinstance(roots,list) or len(roots)!=12 or len(set(roots))!=12:
        errors.append("ROOT_SET_INVALID")
        roots=[]
    if not isinstance(rows,list):
        return ["NODES_NOT_LIST"]
    nodes={}
    unsupported=set()
    for row in rows:
        if not isinstance(row,dict):
            errors.append("NODE_NOT_OBJECT"); continue
        nid=row.get("id"); typ=row.get("type"); status=row.get("status")
        if not isinstance(nid,str) or not nid or nid in nodes:
            errors.append("NODE_ID_INVALID_OR_DUPLICATE"); continue
        if typ not in PRIMITIVES:
            unsupported.add(str(typ))
        if status not in STATUSES:
            errors.append("NODE_STATUS_INVALID:"+nid)
        deps=row.get("depends_on",[])
        defeats=row.get("defeated_by",[])
        if not isinstance(deps,list) or not isinstance(defeats,list):
            errors.append("NODE_REFERENCES_INVALID:"+nid)
        nodes[nid]=row
    if unsupported:
        errors.append("UNSUPPORTED_TYPES:"+",".join(sorted(unsupported)))
    for rid in roots:
        if rid not in nodes:
            errors.append("ROOT_NODE_MISSING:"+rid)
    all_refs=set()
    for row in nodes.values():
        all_refs.update(row.get("depends_on",[]) or [])
        all_refs.update(row.get("defeated_by",[]) or [])
    for ref in sorted(all_refs-set(nodes)):
        errors.append("DANGLING:"+ref)

    # independent dependency-cycle check
    color={}
    def visit(nid):
        state=color.get(nid,0)
        if state==1:
            errors.append("DEPENDENCY_CYCLE:"+nid); return
        if state==2 or nid not in nodes:
            return
        color[nid]=1
        for dep in nodes[nid].get("depends_on",[]) or []:
            visit(dep)
        color[nid]=2
    for rid in roots:
        visit(rid)

    challenges=catalog.get("challenges")
    if not isinstance(challenges,list) or len(challenges)!=70 or catalog.get("challenge_count")!=70:
        errors.append("CHALLENGE_COUNT_INVALID")
        challenges=[]
    seen=set(); covered=set()
    for ch in challenges:
        cid=ch.get("id"); refs=set(ch.get("root_ids") or [])
        if not cid or cid in seen:
            errors.append("CHALLENGE_ID_INVALID_OR_DUPLICATE"); continue
        seen.add(cid)
        if not refs or not refs.issubset(set(roots)):
            errors.append("CHALLENGE_ROOT_MAPPING_INVALID:"+cid)
        covered |= refs
        node=nodes.get(cid)
        if not node or node.get("type")!="DEFEATER" or node.get("status")!="OPEN":
            errors.append("DEFEATER_NODE_INVALID:"+cid)
        for rid in refs:
            if cid not in (nodes.get(rid,{}).get("defeated_by") or []):
                errors.append("ROOT_DEFEATER_BINDING_MISSING:"+rid+":"+cid)
        if ch.get("terminal_pass_forbidden") is not True:
            errors.append("TERMINAL_PASS_NOT_FORBIDDEN:"+cid)
    if covered!=set(roots):
        errors.append("ROOT_WITHOUT_CHALLENGE")

    for rid in roots:
        rn=nodes.get(rid,{})
        if rn.get("type")!="CLAIM" or rn.get("status")!="SUPPORTED":
            errors.append("ROOT_CLAIM_INVALID:"+rid)
        deps=rn.get("depends_on") or []
        if len(deps)!=1:
            errors.append("ROOT_OBLIGATION_CARDINALITY:"+rid); continue
        ob=nodes.get(deps[0],{})
        if ob.get("type")!="OBLIGATION" or ob.get("status")!="OPEN":
            errors.append("ROOT_OBLIGATION_NOT_OPEN:"+rid)
    return sorted(set(errors))

def closure(graph):
    nodes={n["id"]:n for n in graph["nodes"]}
    unsupported=sorted({str(n.get("type")) for n in graph["nodes"] if n.get("type") not in PRIMITIVES})
    memo={}
    active=set(); unresolved=set(); open_ids=set()
    def closed(nid):
        if nid in memo: return memo[nid]
        n=nodes[nid]; status=n.get("status")
        if status=="PROVEN_IRRELEVANT":
            memo[nid]=True; return True
        if status in {"OPEN","STALE","REJECTED"}:
            open_ids.add(nid); memo[nid]=False; return False
        for did in n.get("defeated_by",[]) or []:
            ds=nodes[did].get("status")
            if ds=="SUPPORTED":
                active.add(did); memo[nid]=False; return False
            if ds in {"OPEN","STALE"}:
                unresolved.add(did); open_ids.add(did); memo[nid]=False; return False
        deps=n.get("depends_on",[]) or []
        if not deps:
            ok=n.get("type") in LEAF_TYPES and n.get("authoritative_leaf") is True
            if not ok: open_ids.add(nid)
            memo[nid]=ok; return ok
        ok=True
        for dep in deps:
            if not closed(dep):
                ok=False
        memo[nid]=ok; return ok
    root_closed={rid:closed(rid) for rid in graph["root_ids"]}
    return {
        "representation_closure":not unsupported,
        "proof_closure":all(root_closed.values()) and not active and not unresolved,
        "root_closed":root_closed,
        "unsupported_primitive_types":unsupported,
        "new_primitive_required":bool(unsupported),
        "open_ids":sorted(open_ids),
        "unresolved_defeaters":sorted(unresolved),
    }

def main():
    graph=load_exact(GRAPH_PATH,EXPECTED_GRAPH_BLOB)
    catalog=load_exact(CATALOG_PATH,EXPECTED_CATALOG_BLOB)
    errors=validate(graph,catalog)
    assert not errors,errors
    base=closure(graph)
    assert base["representation_closure"] is True,base
    assert base["proof_closure"] is False,base
    assert base["new_primitive_required"] is False,base
    assert any(base["root_closed"][r] is False for r in graph["root_ids"]),base

    # Canary 1: unsupported primitive must create a representation gap.
    g=copy.deepcopy(graph)
    g["nodes"].append({"id":"ALIEN","type":"UNMODELED_QUALITY_MAGIC","status":"OPEN","depends_on":[],"defeated_by":[]})
    g["nodes"][0]["depends_on"]=["ALIEN"]
    out=closure(g)
    assert out["new_primitive_required"] is True and "UNMODELED_QUALITY_MAGIC" in out["unsupported_primitive_types"],out

    # Canary 2: unmapped catalog challenge must fail binding validation.
    c=copy.deepcopy(catalog)
    c["challenges"].append({"id":"C999","root_ids":["R999"],"attack":"canary","status":"OPEN","terminal_pass_forbidden":True})
    c["challenge_count"]=71
    assert any("CHALLENGE_ROOT_MAPPING_INVALID:C999"==e for e in validate(graph,c)),validate(graph,c)

    # Canary 3: deleting a referenced defeater must fail exact binding.
    g=copy.deepcopy(graph)
    victim=catalog["challenges"][0]["id"]
    g["nodes"]=[n for n in g["nodes"] if n["id"]!=victim]
    assert any(e=="DANGLING:"+victim or e.startswith("DEFEATER_NODE_INVALID:"+victim) for e in validate(g,catalog)),validate(g,catalog)

    # Canary 4: resolving all defeaters cannot self-close still-open evidence obligations.
    g=copy.deepcopy(graph)
    for n in g["nodes"]:
        if n.get("type")=="DEFEATER":
            n["status"]="PROVEN_IRRELEVANT"
    out=closure(g)
    assert out["proof_closure"] is False,out

    # Canary 5: caller cannot turn an OBLIGATION into an authoritative leaf by status alone.
    g=copy.deepcopy(graph)
    for n in g["nodes"]:
        if n.get("type")=="DEFEATER":
            n["status"]="PROVEN_IRRELEVANT"
        if n.get("type")=="OBLIGATION":
            n["status"]="SUPPORTED"
    out=closure(g)
    assert out["proof_closure"] is False,out

    receipt={
        "schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_INDEPENDENT_VERIFY_V1",
        "status":"PASS__INDEPENDENT_STRUCTURAL_DOMAIN_BINDING",
        "brain_graph_git_blob_sha":EXPECTED_GRAPH_BLOB,
        "brain_catalog_git_blob_sha":EXPECTED_CATALOG_BLOB,
        "root_count":12,
        "challenge_count":70,
        "representation_closure":True,
        "proof_closure":False,
        "execution_closure":False,
        "adversarial_closure":False,
        "new_primitive_required":False,
        "negative_canaries_killed":5,
        "professional_quality_closed":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
