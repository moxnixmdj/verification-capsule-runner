from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "root2_output_threshold_dag_v1"
RUNTIME = SUBJECT / "canonical" / "runtime" / "threshold_proof_dag_v1.py"
TESTS = SUBJECT / "canonical" / "tests" / "test_threshold_proof_dag_v1.py"
MANIFEST = SUBJECT / "canonical" / "governance" / "ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json"

EXPECTED = {
    RUNTIME: "7a0c715d931dbba05bc9e5ae344e1ead787ea5b8",
    TESTS: "f960b7d75fd5fa597d0dc115705a5fd9211d96ae",
    MANIFEST: "1fba51d15bcfdf6accd90948155517f7c9b98bbb",
}

EXPECTED_IDS = {
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
    "LIVEBENCH_IF_GE_65_7",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "MYSTERYMECHANISM_GE_49_55",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def fail(message: str) -> None:
    raise SystemExit("VERIFY_FAIL:" + message)

for path, expected in EXPECTED.items():
    observed = git_blob_sha(path)
    if observed != expected:
        fail(f"BLOB_MISMATCH:{path.name}:{observed}:{expected}")

manifest = json.loads(MANIFEST.read_text())
if manifest.get("schema") != "PROJECT_BRAIN_ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1":
    fail("MANIFEST_SCHEMA")
if manifest.get("execution_authority") is not False:
    fail("EXECUTION_AUTHORITY_MUST_BE_FALSE")
if manifest.get("promotion_authority") is not False:
    fail("PROMOTION_AUTHORITY_MUST_BE_FALSE")
if manifest.get("fresh_reality_authority") is not False:
    fail("FRESH_REALITY_AUTHORITY_MUST_BE_FALSE")
if manifest.get("accounting", {}).get("acceptance_credit_delta") != 0:
    fail("NONZERO_ACCEPTANCE_CREDIT")
if manifest.get("exact_state", {}).get("root2_touching") != 19:
    fail("ROOT2_TOUCHING_COUNT")
if manifest.get("runtime", {}).get("git_blob_sha") != EXPECTED[RUNTIME]:
    fail("MANIFEST_RUNTIME_BINDING")
if manifest.get("tests", {}).get("git_blob_sha") != EXPECTED[TESTS]:
    fail("MANIFEST_TEST_BINDING")

predicates = manifest.get("predicates")
if not isinstance(predicates, list) or len(predicates) != 19:
    fail("PREDICATE_COUNT")
ids = {row.get("id") for row in predicates if isinstance(row, dict)}
if ids != EXPECTED_IDS:
    fail("PREDICATE_IDENTITY_SET")

counts = {}
for row in predicates:
    cls = row.get("class")
    counts[cls] = counts.get(cls, 0) + 1
if counts != {
    "ADDITIVE_THRESHOLD": 11,
    "GATED_WEIGHTED_THRESHOLD": 1,
    "RELATIVE_RATING_THRESHOLD": 3,
    "MATCHED_NONINFERIORITY": 4,
}:
    fail("METRIC_CLASS_PARTITION:" + repr(counts))

sys.path.insert(0, str(SUBJECT))
from canonical.runtime.threshold_proof_dag_v1 import INPUT_SCHEMA, compile_threshold_proof_dag

SHA = "a" * 40

def receipt(path="target.json"):
    return {"path": path, "git_blob_sha": SHA}

# Independent adversarial check 1:
# absolute performance must never settle a relative rating target.
relative = {
    "schema": INPUT_SCHEMA,
    "target": {
        "id": "PROWORK_GDPVAL_GE_1846",
        "metric_kind": "RELATIVE_RATING_THRESHOLD",
        "receipt": receipt(),
        "threshold_rating": 1846,
    },
    "allow_fresh_reality": False,
    "actions": [{
        "action_id": "absolute-only",
        "critical_path_seconds": 1,
        "zero_reality": True,
        "coverage_ids": ["absolute"],
        "depends_on": [],
        "route_class": "ABSOLUTE_PROOF",
    }],
}
out = compile_threshold_proof_dag(relative)
if out.get("compiled", {}).get("minimum_pass_cut") is not None:
    fail("RELATIVE_NONTRANSPORT_BROKEN")

# Independent adversarial check 2:
# a zero-reality action depending transitively on fresh reality must be blocked.
transitive = {
    "schema": INPUT_SCHEMA,
    "target": {
        "id": "X",
        "metric_kind": "ADDITIVE_THRESHOLD",
        "receipt": receipt(),
        "total_mass": 10,
        "threshold_mass": 5,
        "current_lower_mass": 0,
        "current_upper_mass": 10,
    },
    "allow_fresh_reality": False,
    "actions": [
        {
            "action_id": "fresh",
            "critical_path_seconds": 1,
            "zero_reality": False,
            "coverage_ids": ["fresh"],
            "depends_on": [],
            "lower_gain_if_pass": 5,
        },
        {
            "action_id": "mid",
            "critical_path_seconds": 1,
            "zero_reality": True,
            "coverage_ids": ["mid"],
            "depends_on": ["fresh"],
            "lower_gain_if_pass": 0,
        },
        {
            "action_id": "top",
            "critical_path_seconds": 1,
            "zero_reality": True,
            "coverage_ids": ["top"],
            "depends_on": ["mid"],
            "lower_gain_if_pass": 5,
        },
    ],
}
out = compile_threshold_proof_dag(transitive)
blocked = set(out.get("blocked_fresh_reality_actions", []))
if blocked != {"fresh", "mid", "top"}:
    fail("TRANSITIVE_FRESH_BLOCK_BROKEN:" + repr(blocked))
if out.get("compiled", {}).get("minimum_pass_cut") is not None:
    fail("TRANSITIVE_FRESH_ROUTE_LEAK")

# Independent adversarial check 3:
# overlapping score coverage must not be double-counted into a false pass route.
overlap = {
    "schema": INPUT_SCHEMA,
    "target": {
        "id": "Y",
        "metric_kind": "ADDITIVE_THRESHOLD",
        "receipt": receipt(),
        "total_mass": 10,
        "threshold_mass": 8,
        "current_lower_mass": 4,
        "current_upper_mass": 10,
    },
    "allow_fresh_reality": False,
    "actions": [
        {
            "action_id": "a",
            "critical_path_seconds": 1,
            "zero_reality": True,
            "coverage_ids": ["same"],
            "depends_on": [],
            "lower_gain_if_pass": 2,
        },
        {
            "action_id": "b",
            "critical_path_seconds": 1,
            "zero_reality": True,
            "coverage_ids": ["same"],
            "depends_on": [],
            "lower_gain_if_pass": 2,
        },
    ],
}
out = compile_threshold_proof_dag(overlap)
if out.get("compiled", {}).get("minimum_pass_cut") is not None:
    fail("OVERLAP_DOUBLE_COUNT")

print(json.dumps({
    "schema": "PROJECT_BRAIN_ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_INDEPENDENT_VERIFIER_V1",
    "pass": True,
    "exact_subject_blobs": {p.name: s for p, s in EXPECTED.items()},
    "predicate_count": 19,
    "metric_class_counts": counts,
    "adversarial_checks": [
        "RELATIVE_RATING_NONTRANSPORT",
        "TRANSITIVE_FRESH_REALITY_BLOCK",
        "OVERLAPPING_COVERAGE_NO_DOUBLE_COUNT",
    ],
    "acceptance_credit_delta": 0,
    "execution_authority": False,
    "promotion_authority": False,
    "fresh_reality_authority": False,
}, sort_keys=True))
