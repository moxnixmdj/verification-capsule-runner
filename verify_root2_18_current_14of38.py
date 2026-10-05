from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJ = ROOT / "subject/root2_18_current_14of38/canonical/governance"

EXPECTED_18 = {
    "CODING_TB4_GE_66_4",
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_CURSORBENCH_GE_57_8",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "HLE_TOOLS_GE_67_7",
    "TB_SCIENCE_GE_58_7",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_AGENT_V2_GE_58_59",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "MYSTERYMECHANISM_GE_49_55",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)

dag_path = SUBJ / "ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V2.json"
root_path = SUBJ / "TERMINAL_ROOT_CAUSE_STATE_V1.json"
ledger_path = SUBJ / "OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"

dag = json.loads(dag_path.read_text())
root = json.loads(root_path.read_text())
ledger = json.loads(ledger_path.read_text())

assert dag["schema"] == "PROJECT_BRAIN_ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V2"
assert dag["source_bindings"]["root_state"]["git_blob_sha"] == blob_sha(root_path)
assert dag["source_bindings"]["evidence_ledger"]["git_blob_sha"] == blob_sha(ledger_path)

assert root["current_acceptance"] == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 14,
    "unresolved_atomic": 24,
    "total_families": 19,
    "total_atomic": 38,
    "terminal": False,
}

assert dag["exact_state"] == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 14,
    "unresolved_atomic": 24,
    "root1_only": 0,
    "root2_only": 15,
    "root3_only": 6,
    "root2_and_root3": 3,
    "root2_touching": 18,
}

partition_matches = []
for d in walk(root):
    keys = {"root1_only","root2_only","root3_only","root2_and_root3"}
    if keys.issubset(d):
        if (
            d["root1_only"] == 0
            and d["root2_only"] == 15
            and d["root3_only"] == 6
            and d["root2_and_root3"] == 3
        ):
            partition_matches.append(d)
assert partition_matches, "CURRENT_ROOT_PARTITION_0_15_6_3_NOT_FOUND"

preds = dag["predicates"]
ids = [p["id"] for p in preds]
assert len(ids) == 18
assert len(set(ids)) == 18
assert set(ids) == EXPECTED_18
assert "LIVEBENCH_IF_GE_65_7" not in ids
assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in ids

assert dag["derivation"]["prior_root2_touching"] == 19
assert dag["derivation"]["current_root2_touching"] == 18
assert dag["derivation"]["removed_predicate"] == "LIVEBENCH_IF_GE_65_7"
assert dag["derivation"]["route_mutations_for_remaining_predicates"] == 0
assert "ROOT3_ONLY" in dag["derivation"]["post_unknown_domain_rule"]

assert dag["scheduling_authority"] is False
assert dag["execution_authority"] is False
assert dag["promotion_authority"] is False
assert dag["fresh_reality_authority"] is False

sat = ledger.get("saturation", {})
assert sat.get("proved_predicate_count") == 14
assert sat.get("unresolved_predicate_count") == 24

print(json.dumps({
    "status": "PASS__EXACT_CURRENT_14_OF_38__ROOT2_18_SET_IDENTITY__ROUTE_MUTATIONS_ZERO",
    "root_blob": blob_sha(root_path),
    "ledger_blob": blob_sha(ledger_path),
    "dag_blob": blob_sha(dag_path),
    "root_partition": {"root1_only":0,"root2_only":15,"root3_only":6,"root2_and_root3":3},
    "root2_touching": 18,
    "predicate_ids": sorted(ids),
    "scheduling_credit": 0,
    "acceptance_credit": 0,
}, indent=2, sort_keys=True))
