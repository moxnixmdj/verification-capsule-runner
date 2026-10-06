#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root2_clean_livebench_18"
OUT=ROOT/"root2_clean_livebench_18_rebind_receipt.json"

FILES={
 "v2":(SUB/"ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V2.json","99c423757b8d690840feb5053ac1be8eb4b4de87"),
 "projection":(SUB/"ROOT2_POST_CLEAN_LIVEBENCH_18_PROJECTION_V1.json","d4af381cd2b7ed325288c69f438ae99b0caa6fb1"),
 "prior":(SUB/"PRIOR_VERIFIED_ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json","1fba51d15bcfdf6accd90948155517f7c9b98bbb"),
 "prior_verification":(SUB/"PRIOR_ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_PUBLIC_RUNNER_VERIFICATION.json","553602570334f39003708e52d781b8c59f27eb7c"),
}
LIVEBENCH="LIVEBENCH_IF_GE_65_7"

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name):
    p,sha=FILES[name]
    got=blob(p)
    assert got==sha,(name,got,sha)
    return json.loads(p.read_text())

def main():
    v2=load("v2")
    projection=load("projection")
    prior=load("prior")
    prior_ver=load("prior_verification")

    assert prior_ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert prior_ver["subject"]["manifest_git_blob_sha"]==FILES["prior"][1]
    assert prior_ver["subject"]["runtime_git_blob_sha"]=="7a0c715d931dbba05bc9e5ae344e1ead787ea5b8"

    prior_by_id={x["id"]:x for x in prior["predicates"]}
    new_by_id={x["id"]:x for x in v2["predicates"]}
    assert len(prior_by_id)==19
    assert len(new_by_id)==18
    assert LIVEBENCH in prior_by_id
    assert LIVEBENCH not in new_by_id
    assert set(new_by_id)==set(prior_by_id)-{LIVEBENCH}
    for pid,item in new_by_id.items():
        assert item==prior_by_id[pid],("ROUTE_DRIFT",pid)

    pset=set(projection["exact_root2_touching"])
    assert len(pset)==18
    assert pset==set(new_by_id)
    assert set(projection["root2_only"]) | set(projection["root2_and_root3"]) == pset
    assert set(projection["root2_only"]).isdisjoint(set(projection["root2_and_root3"]))
    assert len(projection["root2_only"])==15
    assert len(projection["root2_and_root3"])==3
    assert projection["removed_predicate"]==LIVEBENCH

    assert projection["counts"]=={
      "proved_atomic":13,"unresolved_atomic":25,"root1_only":0,
      "root2_only":15,"root3_only":7,"root2_and_root3":3,"root2_touching":18
    }
    assert v2["exact_state"]=={
      "accepted_families":5,"open_families":14,"proved_atomic":13,"unresolved_atomic":25,
      "root1_only":0,"root2_only":15,"root3_only":7,"root2_and_root3":3,"root2_touching":18
    }
    sb=v2["source_bindings"]
    assert sb["evidence_ledger"]["git_blob_sha"]=="25d3408c7ee746f0f853d718ffa1af1ecff14596"
    assert sb["root_state"]["git_blob_sha"]=="1a94fa8f0961edc420a56f6e7c2ca8764be67373"
    assert sb["clean_livebench_reduction"]["git_blob_sha"]=="5e9d6d560f7ff6a3a8a6e8cff7d52e31cd71d957"
    assert sb["clean_livebench_verification"]["git_blob_sha"]=="57e27e3c56372b57a1d4e0255f49340d4a4c8588"
    assert sb["prior_verified_19_subject"]["git_blob_sha"]==FILES["prior"][1]
    assert v2["runtime"]["git_blob_sha"]==prior["runtime"]["git_blob_sha"]
    assert v2["proof_precedence"]==prior["proof_precedence"]

    receipt={
      "schema":"PROJECT_BRAIN_ROOT2_POST_CLEAN_LIVEBENCH_18_REBIND_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__EXACT_CURRENT_18_EQUALS_PRIOR_VERIFIED_19_MINUS_LIVEBENCH__ZERO_ROUTE_DRIFT__SCHEDULING_ONLY",
      "verified":{
        "prior_touching":19,"current_touching":18,"removed":[LIVEBENCH],
        "surviving_route_mutations":0,
        "current_partition":{"root1_only":0,"root2_only":15,"root3_only":7,"root2_and_root3":3,"unresolved_total":25},
        "runtime_blob":v2["runtime"]["git_blob_sha"],
        "proof_precedence_unchanged":True,
      },
      "subject_blobs":{k:sha for k,(_,sha) in FILES.items()},
      "authority":{"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False},
      "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"acceptance_credit_delta":0}
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
