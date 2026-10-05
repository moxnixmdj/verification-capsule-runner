#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"current_authority_wake_root2"
OUT=ROOT/"current_authority_wake_root2_reconcile_receipt.json"

FILES={
 "root_candidate":(SUB/"CANDIDATE_TERMINAL_ROOT_CAUSE_STATE_V1.json","de8a67f653339af2486ace2d6974062b5766a227"),
 "authority_candidate":(SUB/"CANDIDATE_CURRENT_TERMINAL_AUTHORITY_V1.json","50a4004a3f17a462ba94c9819f53f7b9aba6b26c"),
 "root_baseline":(SUB/"BASELINE_TERMINAL_ROOT_CAUSE_STATE_V1.json","7c1ed0adf243b92abab2cbdb6ebced921dcbb860"),
 "authority_baseline":(SUB/"BASELINE_CURRENT_TERMINAL_AUTHORITY_V1.json","9015b1fcacb40222f920c124986fcea63cc6e5ee"),
 "wake":(SUB/"ROOT2_18_WAKE_AWARE_EXECUTABLE_CUT_V3.json","d09abed23287560508353ce0e0476b98a9749cef"),
 "v4_activation":(SUB/"ROOT2_18_CURRENT_14_24_CURSOR_ROUTE_V4_ACTIVATION_V1.json","d739ade25b0c00cee069add72dab9677fa31e027"),
 "v4_subject":(SUB/"ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V4.json","07712a3e66b6048053a87c5a693b370512195d8f"),
 "scope6":(SUB/"SIX_BENCHMARK_PROXY_SCOPE_REPAIR_FRONTIER_V3_ACTIVATION_V1.json","2cdcb6eb87a9303cd407998264450e6e8552cd61"),
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name):
    p,expected=FILES[name]
    got=blob(p)
    assert got==expected,(name,got,expected)
    return json.loads(p.read_text(encoding="utf-8"))

_MISSING=object()
def diff_paths(a,b,path=""):
    out=[]
    if type(a) is not type(b):
        return [path or "<root>"]
    if isinstance(a,dict):
        for k in sorted(set(a)|set(b)):
            p=f"{path}.{k}" if path else k
            if k not in a or k not in b:
                out.append(p)
            else:
                out.extend(diff_paths(a[k],b[k],p))
        return out
    if isinstance(a,list):
        if len(a)!=len(b):
            out.append(path+".length")
        for i,(x,y) in enumerate(zip(a,b)):
            out.extend(diff_paths(x,y,f"{path}[{i}]"))
        return out
    if a!=b:
        out.append(path)
    return out

def allowed(path,prefixes):
    return any(path==p or path.startswith(p+".") or path.startswith(p+"[") for p in prefixes)

def main()->int:
    rc=load("root_candidate"); rb=load("root_baseline")
    ac=load("authority_candidate"); ab=load("authority_baseline")
    wake=load("wake"); v4a=load("v4_activation"); v4=load("v4_subject"); scope6=load("scope6")

    # Baseline truth is already 14/24; this patch may not change acceptance or root partition.
    assert rb["current_acceptance"]==rc["current_acceptance"]=={
      "accepted_families":5,"open_families":14,"proved_atomic":14,"unresolved_atomic":24,
      "total_families":19,"total_atomic":38,"terminal":False
    }
    assert rb["current_residual_root_partition"]==rc["current_residual_root_partition"]
    p=rc["current_residual_root_partition"]
    assert p["root1_positive_gap_count"]==0
    assert p["root2_only_count"]==15 and p["root2_and_root3_count"]==3
    assert p["root3_only_count"]==6 and p["unresolved_total"]==24

    root_allowed={
      "scheduler_policy.root2_current_frontier",
      "scheduler_policy.root2_current_frontier_git_blob_sha",
      "scheduler_policy.root2_effective_scheduling_authority",
      "scheduler_policy.root2_effective_scheduling_authority_source",
      "scheduler_policy.root2_effective_scheduling_scope",
      "scheduler_policy.root2_current_scheduling_compiler",
      "scheduler_policy.root2_current_scheduling_compiler_git_blob_sha",
      "scheduler_policy.root2_current_scheduling_activation",
      "scheduler_policy.root2_current_wake_aware_executable_cut",
      "scheduler_policy.root2_prior_wake_aware_v2_activation",
      "scheduler_policy.root2_output_only_threshold_dag.current_effective_state",
      "scheduler_policy.root2_post_livebench_18_rebind.status",
      "scheduler_policy.root2_post_livebench_18_rebind.current_partition_activation_path",
      "scheduler_policy.root2_post_livebench_18_rebind.current_partition_activation_git_blob_sha",
      "scheduler_policy.adaptive_meta_scheduler.currentness_note",
      "scheduler_policy.root2_authority_reconciliation",
    }
    rdiff=diff_paths(rc,rb)
    unexpected=[x for x in rdiff if not allowed(x,root_allowed)]
    assert not unexpected,("UNEXPECTED_ROOT_MUTATIONS",unexpected[:25])

    sp=rc["scheduler_policy"]
    assert sp["root2_current_frontier"]=="canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V4.json"
    assert sp["root2_current_frontier_git_blob_sha"]==FILES["v4_subject"][1]
    assert sp["root2_current_scheduling_compiler_git_blob_sha"]==FILES["v4_subject"][1]
    assert sp["root2_effective_scheduling_authority"] is True
    assert sp["root2_effective_scheduling_authority_source"]=="canonical/governance/ROOT2_18_WAKE_AWARE_EXECUTABLE_CUT_V3.json"
    assert sp["root2_current_scheduling_activation"]["git_blob_sha"]==FILES["v4_activation"][1]
    assert sp["root2_current_wake_aware_executable_cut"]["git_blob_sha"]==FILES["wake"][1]
    assert sp["root2_current_wake_aware_executable_cut"]["active_information_positive_group_count"]==6
    assert sp["root2_current_wake_aware_executable_cut"]["execution_authority"] is False
    assert sp["root2_current_wake_aware_executable_cut"]["promotion_authority"] is False
    assert sp["root2_current_wake_aware_executable_cut"]["fresh_reality_authority"] is False
    assert all(v==0 for v in sp["root2_authority_reconciliation"].values() if isinstance(v,(int,float)))

    # Bound active sources must themselves be exact and fail-closed.
    assert v4a["subject"]["git_blob_sha"]==FILES["v4_subject"][1]
    assert v4a["authority"]=={"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
    assert v4["exact_state"]["proved_atomic"]==14 and v4["exact_state"]["unresolved_atomic"]==24
    assert v4["exact_state"]["root2_touching"]==18
    assert wake["scheduling_authority"] is True
    assert wake["execution_authority"] is False and wake["promotion_authority"] is False and wake["fresh_reality_authority"] is False
    assert wake["scheduler_delta"]["active_group_count"]==6
    assert wake["deferred_fresh_reality"]["execution_authority"] is False
    assert "DO_NOT_TREAT_THAT_PREDICATE_SCOPE_CERTIFICATE_AS_UNIVERSAL_WHOLE_EVIDENCE_TO_AUDIENCE_SYNTHESIS_001_TYPED_INPUT_DOMAIN_COMPLETENESS"==wake["synthesis_truth_repair"]["revoke_for_scheduling"]
    assert scope6["scheduling_authority"] is True
    assert scope6["execution_authority"] is False and scope6["promotion_authority"] is False and scope6["fresh_reality_authority"] is False

    # Top-level authority changes are tightly whitelisted; acceptance and root overlay are byte-semantically unchanged.
    authority_allowed={
      "sources.terminal_root_cause_state",
      "sources.terminal_root_cause_state_v1",
      "sources.root2_current_exact18_v4_activation",
      "sources.root2_wake_aware_executable_cut_v3",
      "sources.six_benchmark_proxy_scope_repair_frontier_v3_activation",
      "root2_current_scheduler_overlay",
      "next",
      "next_terminal_action",
      "current_scheduler_truth_reconciliation",
    }
    adiff=diff_paths(ac,ab)
    unexpected=[x for x in adiff if not allowed(x,authority_allowed)]
    assert not unexpected,("UNEXPECTED_AUTHORITY_MUTATIONS",unexpected[:25])
    assert ac["status"]==ab["status"]
    assert ac["atomic_acceptance_frontier"]==ab["atomic_acceptance_frontier"]
    assert ac["current_root_partition_override"]==ab["current_root_partition_override"]

    for k in ("terminal_root_cause_state","terminal_root_cause_state_v1"):
        assert ac["sources"][k]["git_blob_sha"]==FILES["root_candidate"][1]
        assert "14_PROVED__24_UNRESOLVED" in ac["sources"][k]["status"]
    assert ac["sources"]["root2_current_exact18_v4_activation"]["git_blob_sha"]==FILES["v4_activation"][1]
    assert ac["sources"]["root2_wake_aware_executable_cut_v3"]["git_blob_sha"]==FILES["wake"][1]
    assert ac["sources"]["six_benchmark_proxy_scope_repair_frontier_v3_activation"]["git_blob_sha"]==FILES["scope6"][1]

    s=ac["root2_current_scheduler_overlay"]
    assert s["effective_touching_predicate_count"]==18
    assert s["scheduling_authority"] is True
    assert s["execution_authority"] is False and s["promotion_authority"] is False and s["fresh_reality"] is False
    assert s["activation_git_blob_sha"]==FILES["v4_activation"][1]
    assert s["compilation_git_blob_sha"]==FILES["v4_subject"][1]
    assert s["wake_aware_executable_cut_git_blob_sha"]==FILES["wake"][1]
    assert s["active_information_positive_group_count"]==6
    assert s["deferred_fresh_reality_predicate"]=="TB_SCIENCE_GE_58_7"

    assert ac["next"]==ac["next_terminal_action"]
    assert "SOLVE_MINIMUM_ZERO_REALITY_CERTIFICATE_CUT" not in ac["next"]
    assert "RUN_ACTIVE_WAKE_AWARE_ROOT2_ZERO_REALITY_GROUPS_WHERE_INFORMATION_POSITIVE" in ac["next"]
    assert "RECOMPUTE_ROOT3_9_TOUCHING_EVENT_SET" in ac["next"]
    assert "NO_FRESH_REALITY_UNTIL_EXPLICIT_AUTHORITY" in ac["next"]
    tr=ac["current_scheduler_truth_reconciliation"]
    assert tr["root_state_git_blob_sha"]==FILES["root_candidate"][1]
    assert tr["root2_wake_aware_executable_v3_git_blob_sha"]==FILES["wake"][1]
    assert all(v==0 for v in tr["accounting"].values())

    receipt={
      "schema":"PROJECT_BRAIN_CURRENT_AUTHORITY_WAKE_ROOT2_RECONCILIATION_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__CURRENT_14_24_ROOT_CONTENT_ADDRESSED__ACTIVE_EXACT18_V4_AND_WAKE_V3_BOUND__STALE_SOLVE_CUT_DISPATCH_DELETED__ZERO_CREDIT",
      "verified":{
        "acceptance_unchanged":"14_PROVED_24_UNRESOLVED",
        "root_partition_unchanged":{"root1":0,"root2_only":15,"root3_only":6,"mixed":3,"root2_touching":18},
        "root_changes_confined_to_scheduler_policy":True,
        "authority_changes_confined_to_sources_scheduler_and_dispatch":True,
        "active_root2_information_positive_groups":6,
        "root3_9_recompute_preserved":True,
        "fresh_reality_authority":False,
        "execution_authority":False,
        "promotion_authority":False,
      },
      "subject_blobs":{k:sha for k,(_,sha) in FILES.items()},
      "semantic_effect":"ELIMINATE_SPLIT_BRAIN_CONTROL_PLANE_STALENESS_WITHOUT_CHANGING_ACCEPTANCE_OR_GRANTING_EXECUTION__BIND_CURRENT_ROOT_AND_ACTIVE_WAKE_AWARE_ROOT2_SCHEDULER",
      "authority":{"scheduling_reconciliation_eligible":True,"execution":False,"promotion":False,"fresh_reality":False},
      "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
