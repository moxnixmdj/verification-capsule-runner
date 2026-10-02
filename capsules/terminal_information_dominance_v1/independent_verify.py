import hashlib
import json
from pathlib import Path

from canonical.runtime.terminal_information_dominance_v1 import evaluate

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/terminal_information_dominance_v1.py": "f10986bd09a7cc64a1fae3c6ea8e69b5655f2199",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json": "106139ff69616670993dbc6af324d8686747e8b1",
    "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V2.json": "01f6bc32d6661202d9a41b52d82e9ec56c8a660c",
    "canonical/tests/test_terminal_information_dominance_v1.py": "c934774d1d8c659522da85ba5bde5354d7890bfa",
}


def git_blob_sha(path):
    data = (ROOT / path).read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


for path, expected in EXPECTED.items():
    actual = git_blob_sha(path)
    assert actual == expected, (path, actual, expected)

frontier = json.loads(
    (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json").read_text(encoding="utf-8")
)
activation = json.loads(
    (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V2.json").read_text(encoding="utf-8")
)

out = evaluate(frontier)
assert out["status"] == "EXACT_INFORMATION_DOMINANCE_COMPUTED", out
assert out["unresolved_predicate_count"] == 31, out
assert out["certificate_count"] == 15, out
assert out["reality_cost_degenerate_for_ordering"] is True, out
assert out["highest_direct_coverage_count"] == 11, out
assert out["highest_direct_coverage_certificate_ids"] == ["MATCHED_SCOPE_BINDING_CERTIFICATE"], out
assert out["dominated_certificate_ids"] == [], out
assert len(out["best_full_frontier_bundle"]["certificate_ids"]) == 15, out
assert out["best_full_frontier_bundle"]["covered_predicate_count"] == 31, out
assert out["best_full_frontier_bundle"]["unique_requirement_count"] == 20, out
assert out["best_full_frontier_bundle"]["new_reality_units"] == 0, out

by_id = {row["id"]: row for row in frontier["certificates"]}
tool_req = set(by_id["TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"]["requires"])
deleg_req = set(by_id["DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"]["requires"])
assert tool_req.isdisjoint(deleg_req), (tool_req, deleg_req)
assert set(by_id["MATCHED_SCOPE_BINDING_CERTIFICATE"]["target_predicates"]).isdisjoint(
    {"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"}
)

assert activation["status"].startswith("FAIL_CLOSED"), activation
assert activation["replacement_candidate"] == "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json"
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print("independent terminal information dominance verification: PASS")
