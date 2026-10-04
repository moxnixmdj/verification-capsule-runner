#!/usr/bin/env python3
import json, hashlib

CURRENT_ROOT_BLOB = "e8371418ed39b83b14df874c8eb5e0bdb6a2e603"
DAG_MANIFEST_BLOB = "1fba51d15bcfdf6accd90948155517f7c9b98bbb"
CURRENT_ROOT_SEAL_BLOB = "8429fdbf97f0b045a6ea54e3cae3e2413b9acdae"
PRIOR_DAG_VERIFICATION_BLOB = "553602570334f39003708e52d781b8c59f27eb7c"
CANDIDATE_BLOB = "b9879e919e3b5ebc5e41162c9b7a63bf15f1fd13"

CURRENT = ["AGENCY_MATCHED_SUCCESS_NONINFERIOR","ARTIFACT_AA_BRIEFCASE_GE_1822","AUTOMATIONBENCH_GE_40","CHARTOGRAPHY_TOOLS_GE_89","CODING_CURSORBENCH_GE_57_8","CODING_FRONTIERCODE_GE_54_4","CODING_TB4_GE_66_4","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR","FINANCE_ACCOUNTING_INDEX_GE_61","FINANCE_AGENT_V2_GE_58_59","HLE_TOOLS_GE_67_7","IF_SCOPE_BOUNDARY_NONINFERIOR","LIVEBENCH_IF_GE_65_7","MYSTERYMECHANISM_GE_49_55","OSWORLD_2_1_PARTIAL_GE_81_8","PROWORK_AA_BRIEFCASE_GE_1822","PROWORK_GDPVAL_GE_1846","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR","TB_SCIENCE_GE_58_7"]
VERIFIED_DAG_DOMAIN = ["AGENCY_MATCHED_SUCCESS_NONINFERIOR","ARTIFACT_AA_BRIEFCASE_GE_1822","AUTOMATIONBENCH_GE_40","CHARTOGRAPHY_TOOLS_GE_89","CODING_CURSORBENCH_GE_57_8","CODING_FRONTIERCODE_GE_54_4","CODING_TB4_GE_66_4","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR","FINANCE_ACCOUNTING_INDEX_GE_61","FINANCE_AGENT_V2_GE_58_59","HLE_TOOLS_GE_67_7","IF_SCOPE_BOUNDARY_NONINFERIOR","LIVEBENCH_IF_GE_65_7","MYSTERYMECHANISM_GE_49_55","OSWORLD_2_1_PARTIAL_GE_81_8","PROWORK_AA_BRIEFCASE_GE_1822","PROWORK_GDPVAL_GE_1846","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR","TB_SCIENCE_GE_58_7"]

def main():
    assert len(CURRENT) == 19
    assert len(set(CURRENT)) == 19
    assert len(VERIFIED_DAG_DOMAIN) == 19
    assert len(set(VERIFIED_DAG_DOMAIN)) == 19
    assert sorted(CURRENT) == sorted(VERIFIED_DAG_DOMAIN)
    assert "LIVEBENCH_IF_GE_65_7" in CURRENT

    payload = {
        "schema": "PROJECT_BRAIN_ROOT2_POST_REVOCATION_DAG_REBIND_PUBLIC_WITNESS_V1",
        "current_root_blob": CURRENT_ROOT_BLOB,
        "current_root_seal_blob": CURRENT_ROOT_SEAL_BLOB,
        "dag_manifest_blob": DAG_MANIFEST_BLOB,
        "prior_dag_verification_blob": PRIOR_DAG_VERIFICATION_BLOB,
        "candidate_blob": CANDIDATE_BLOB,
        "current_count": len(CURRENT),
        "dag_count": len(VERIFIED_DAG_DOMAIN),
        "exact_sorted_set_equality": sorted(CURRENT) == sorted(VERIFIED_DAG_DOMAIN),
        "current_set_sha256": hashlib.sha256("\n".join(sorted(CURRENT)).encode()).hexdigest(),
        "dag_set_sha256": hashlib.sha256("\n".join(sorted(VERIFIED_DAG_DOMAIN)).encode()).hexdigest(),
        "missing": sorted(set(CURRENT) - set(VERIFIED_DAG_DOMAIN)),
        "stale": sorted(set(VERIFIED_DAG_DOMAIN) - set(CURRENT)),
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
    }
    assert payload["current_set_sha256"] == payload["dag_set_sha256"]
    assert payload["missing"] == []
    assert payload["stale"] == []
    with open("root2_post_revocation_dag_rebind_receipt.json","w",encoding="utf-8") as f:
        json.dump(payload,f,indent=2,sort_keys=True)
        f.write("\n")
    print(json.dumps(payload,indent=2,sort_keys=True))

if __name__ == "__main__":
    main()
