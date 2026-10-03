#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, pathlib, shutil, sys, tempfile

HERE=pathlib.Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/current_terminal_information_dominance_v2.py":"0fc5bc26e55c3756d3c5d9213f3aa6d0a7b4bb1e",
  "canonical/runtime/current_terminal_scheduling_world_v1.py":"9ae2b990578b042dd24074fd5013378b72e64b6b",
  "canonical/runtime/terminal_information_dominance_v1.py":"f10986bd09a7cc64a1fae3c6ea8e69b5655f2199",
  "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py":"9af1bd62048277cc8c4fabab8efe5d217c367bac",
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
  "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json":"4b5517dbd12978f8ffe481fb775e85592c7790c8",
  "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json":"e29ce3a7c782c7b9ab1097dd3124a917d3fea9d2",
  "canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json":"e56719b8c63078273a6974104d413aa1b643da3b",
  "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"2560dbf990a4f39f006884a2c0d1fa7950e15795",
  "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json":"04f0ee3cd64c3f77b29ece159ac9a35eae47a9dc",
  "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1.json":"c916c095cfb52b4b3d8dd863dfb0be0f05529f2e",
  "canonical/verification/TOOL_DISCOVERY_RETRIEVAL_FRONTIER_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"bbbd34e192aa65ba94c4bda19a1a1eb9c2b5b406",
  "canonical/verification/RESIDUAL_WITNESS_RETRIEVAL_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"f0a68c8219d704875535543060f63b9ecaca6dd5",
  "canonical/runtime/residual_witness_retrieval_compiler_v1.py":"9daa8d590f3356b3fc51eccf75c56cbf515239e4",
  "canonical/runtime/residual_witness_backend_router_v1.py":"578c5f87901a458b12d7df984e0a6a525d367456",
  "canonical/runtime/github_public_retrieval_provider_v1.py":"29b808935559382ab7ddc81aaa08fe0611a05df8",
  "canonical/verification/GITHUB_PUBLIC_RETRIEVAL_SURFACES_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"ca5acd7afbf14b7cce568ec482c160c3795e57ba"
}

def flat(path:str)->pathlib.Path:
    return HERE/path.replace("/","__")

def blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

for rel,expected in EXPECTED.items():
    raw=flat(rel).read_bytes()
    got=blob_sha(raw)
    assert got==expected,(rel,got,expected)

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    for rel in EXPECTED:
        dst=root/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(flat(rel),dst)
    sys.path.insert(0,str(root))

    from canonical.runtime import current_terminal_information_dominance_v2 as subject
    from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as gate

    def load(rel:str):
        return json.loads((root/rel).read_text(encoding="utf-8"))

    gate_result=gate.evaluate_repository(root)
    assert gate_result["pass"] is True,gate_result

    base=[
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        gate_result,
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
    ]

    out=subject.evaluate(*base)
    assert out["pass"] is True,out
    s=out["live_world_summary"]
    assert (s["frozen_predicates"],s["proved_predicates"],s["unresolved_predicates"])==(38,11,27),s
    assert s["live_action_coverage_count"]==27,s
    assert s["tool_discovery_retrieval_gate_required"] is True
    assert s["tool_discovery_retrieval_gate_pass"] is True
    assert out["tool_discovery_target_open"] is True
    assert out["dominance"]["status"]=="EXACT_INFORMATION_DOMINANCE_COMPUTED"
    assert out["dominance"]["unresolved_predicate_count"]==27
    assert out["dominance"]["best_full_frontier_bundle"]["covered_predicate_count"]==27

    covered={p for row in out["dominance"]["single_certificate_structural_front"] for p in row["covered_predicates"]}
    for pid in subject.RECOVERY_PROVED|{subject.DELEGATION_PROVED}:
        assert pid not in covered,(pid,sorted(covered))
    assert subject.TOOL_TARGET in covered

    mutations=0
    a=copy.deepcopy(base)
    a[6]={"schema":gate.SCHEMA,"pass":False,"target_predicate":gate.TARGET}
    m=subject.evaluate(*a)
    assert m["pass"] is False and "MANDATORY_TOOL_DISCOVERY_RETRIEVAL_GATE_NOT_PASS" in m["errors"],m
    mutations+=1

    a=copy.deepcopy(base)
    a[7]["mandatory_tool_discovery_retrieval"]["mandatory"]=False
    m=subject.evaluate(*a)
    assert m["pass"] is False and "CURRENT_SCHEDULING_RETRIEVAL_NOT_MANDATORY" in m["errors"],m
    mutations+=1

    a=copy.deepcopy(base)
    a[7]["mandatory_tool_discovery_retrieval"]["direct_bypass_allowed"]=True
    m=subject.evaluate(*a)
    assert m["pass"] is False and "CURRENT_SCHEDULING_DIRECT_BYPASS_NOT_DISABLED" in m["errors"],m
    mutations+=1

    a=copy.deepcopy(base)
    a[7]["mandatory_tool_discovery_retrieval"]["consumed_source_epoch_replay_allowed"]=True
    m=subject.evaluate(*a)
    assert m["pass"] is False and "CURRENT_SCHEDULING_EPOCH_REPLAY_NOT_DISABLED" in m["errors"],m
    mutations+=1

    assert out["new_reality_units_consumed"]==0
    assert out["incremental_spend_usd"]==0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False

    print("LIVE27_INFORMATION_DOMINANCE_V2_INDEPENDENT_PASS")
    print(json.dumps({
        "brain_pr":1313,
        "candidate_runtime_blob":EXPECTED["canonical/runtime/current_terminal_information_dominance_v2.py"],
        "live_world_summary":out["live_world_summary"],
        "certificate_count":out["dominance"]["certificate_count"],
        "nondominated_zero_reality_certificate_ids":out["nondominated_zero_reality_certificate_ids"],
        "dominated_zero_reality_certificate_ids":out["dominated_zero_reality_certificate_ids"],
        "best_full_frontier_bundle":out["dominance"]["best_full_frontier_bundle"],
        "highest_direct_coverage_count":out["dominance"]["highest_direct_coverage_count"],
        "highest_direct_coverage_certificate_ids":out["dominance"]["highest_direct_coverage_certificate_ids"],
        "mutation_fail_closed_count":mutations,
        "exact_blob_count":len(EXPECTED)
    },sort_keys=True))
