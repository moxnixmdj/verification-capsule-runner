#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root2_current14_exact18_v3"
PRIOR=ROOT/"subject"/"root2_clean_livebench_18"
OUT=ROOT/"root2_current14_exact18_v3_receipt.json"

FILES={
  "v3":(SUB/"ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V3.json","82612b803c1d47eeb8888cf99a00c14a1bea54e1"),
  "root":(SUB/"TERMINAL_ROOT_CAUSE_STATE_V1.json","7c1ed0adf243b92abab2cbdb6ebced921dcbb860"),
  "ledger":(SUB/"OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json","a3fd20e58fdbd9b86278b7de0c245de3063dce27"),
  "unknown_domain":(SUB/"UNKNOWN_DOMAIN_V7_WINDOWS_V8_ACCEPTANCE_REDUCTION_20261005_V1.json","ebe8edcda3e0aa7dcffab6032834532a6f06c5f7"),
  "prior19":(PRIOR/"PRIOR_VERIFIED_ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json","1fba51d15bcfdf6accd90948155517f7c9b98bbb"),
  "prior19_verification":(PRIOR/"PRIOR_ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_PUBLIC_RUNNER_VERIFICATION.json","553602570334f39003708e52d781b8c59f27eb7c"),
}
LIVEBENCH="LIVEBENCH_IF_GE_65_7"

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name):
    p,expected=FILES[name]
    got=blob(p)
    assert got==expected,(name,got,expected)
    return json.loads(p.read_text(encoding="utf-8"))

def main()->int:
    v3=load("v3")
    root=load("root")
    ledger=load("ledger")
    unknown=load("unknown_domain")
    prior=load("prior19")
    prior_ver=load("prior19_verification")

    # Reuse only independently verified route semantics.
    assert prior_ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert prior_ver["subject"]["manifest_git_blob_sha"]==FILES["prior19"][1]
    assert prior_ver["subject"]["runtime_git_blob_sha"]==prior["runtime"]["git_blob_sha"]

    prior_by_id={x["id"]:x for x in prior["predicates"]}
    current_by_id={x["id"]:x for x in v3["predicates"]}
    assert len(prior_by_id)==19
    assert len(current_by_id)==18
    assert LIVEBENCH in prior_by_id and LIVEBENCH not in current_by_id
    assert set(current_by_id)==set(prior_by_id)-{LIVEBENCH}
    for pid,item in current_by_id.items():
        assert item==prior_by_id[pid],("ROUTE_DRIFT",pid)
    assert v3["proof_precedence"]==prior["proof_precedence"]
    assert v3["cross_predicate_reuse"]==prior["cross_predicate_reuse"]
    assert v3["runtime"]["git_blob_sha"]==prior["runtime"]["git_blob_sha"]

    # Recompute the exact live Root2 universe from the pinned current root state.
    ca=root["current_acceptance"]
    part=root["current_residual_root_partition"]
    root2_only=part["root2_only"]
    mixed=part["root2_and_root3"]
    exact=root2_only+mixed
    assert ca=={
      "accepted_families":5,"open_families":14,"proved_atomic":14,
      "unresolved_atomic":24,"total_families":19,"total_atomic":38,"terminal":False
    }
    assert part["root1_positive_gap_count"]==0
    assert part["root2_only_count"]==15
    assert part["root3_only_count"]==6
    assert part["root2_and_root3_count"]==3
    assert len(exact)==18 and len(set(exact))==18
    assert LIVEBENCH not in exact
    assert set(exact)==set(current_by_id)

    # Candidate state must be an exact projection of the pinned authority, not a stale epoch.
    assert v3["exact_state"]=={
      "accepted_families":5,"open_families":14,"proved_atomic":14,
      "unresolved_atomic":24,"root1_only":0,"root2_only":15,
      "root3_only":6,"root2_and_root3":3,"root2_touching":18
    }
    sb=v3["source_bindings"]
    assert sb["root_state"]["git_blob_sha"]==FILES["root"][1]
    assert sb["evidence_ledger"]["git_blob_sha"]==FILES["ledger"][1]
    assert sb["unknown_domain_v8_reduction"]["git_blob_sha"]==FILES["unknown_domain"][1]
    assert sb["predicate_registry"]["git_blob_sha"]==prior["source_bindings"]["predicate_registry"]["git_blob_sha"]

    # The 14th proof is real and is the Root3-only unknown-domain closure; it must not mutate Root2.
    assert unknown["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    assert "14_PROVED__24_UNRESOLVED" in unknown["status"]
    assert unknown["accounting"]["atomic_predicate_proved_delta"]==1
    assert unknown["accounting"]["unresolved_predicate_delta"]==-1
    proved=[x["predicate_id"] for x in ledger["claims"] if x.get("state")=="PROVED"]
    assert len(proved)==14
    assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" in proved
    assert LIVEBENCH in proved

    # Rebind is scheduling-only. No benchmark execution, promotion or fresh reality sneaks in.
    assert v3["scheduling_authority"] is False
    assert v3["execution_authority"] is False
    assert v3["promotion_authority"] is False
    assert v3["fresh_reality_authority"] is False
    assert v3["independent_verification_required"] is True
    assert all(x==0 for x in v3["accounting"].values())

    receipt={
      "schema":"PROJECT_BRAIN_ROOT2_CURRENT14_EXACT18_V3_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__CURRENT_14_24_EXACT_18__PRIOR_VERIFIED_19_MINUS_LIVEBENCH__ZERO_ROUTE_DRIFT__SCHEDULING_ELIGIBLE",
      "verified":{
        "accepted_families":5,"open_families":14,
        "proved_atomic":14,"unresolved_atomic":24,
        "root2_only":15,"root3_only":6,"root2_and_root3":3,
        "root2_touching":18,
        "removed_from_prior_verified_root2":[LIVEBENCH],
        "surviving_route_mutations":0,
        "unknown_domain_root3_only_closure_absorbed":True,
        "proof_precedence_unchanged":True,
        "cross_predicate_reuse_unchanged":True,
        "runtime_blob":v3["runtime"]["git_blob_sha"],
      },
      "subject_blobs":{k:sha for k,(_,sha) in FILES.items()},
      "semantic_effect":"ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V3_IS_ELIGIBLE_FOR_EXPLICIT_SCHEDULING_ACTIVATION_ON_THE_PINNED_14_24_AUTHORITY__NO_EXECUTION_PROMOTION_FRESH_REALITY_OR_ACCEPTANCE_CREDIT",
      "authority":{"scheduling_eligibility":True,"execution":False,"promotion":False,"fresh_reality":False},
      "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
