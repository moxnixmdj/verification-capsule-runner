from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SUB = ROOT_DIR / "subject" / "root2_v13_exact18_20261005_sol"
EXPECTED = {
    "ROOT.json": "7c1ed0adf243b92abab2cbdb6ebced921dcbb860",
    "ACCEPTANCE.json": "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
    "V13.json": "fd800ab5a9464bfcb7364876ef4d2efea7ed4d6e",
}

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for name, expected in EXPECTED.items():
    got = blob_sha(SUB / name)
    assert got == expected, (name, got, expected)

root = json.loads((SUB / "ROOT.json").read_text())
acc = json.loads((SUB / "ACCEPTANCE.json").read_text())
v13 = json.loads((SUB / "V13.json").read_text())

cur = root["current_acceptance"]
assert cur == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 14,
    "unresolved_atomic": 24,
    "total_families": 19,
    "total_atomic": 38,
    "terminal": False,
}

sat = acc["saturation"]
assert sat["proved_predicate_count"] == 14
assert sat["unresolved_predicate_count"] == 24
assert sat["new_reality_units_consumed"] == 0

part = root["current_residual_root_partition"]
assert part["unresolved_total"] == 24
assert part["root1_positive_gap_count"] == 0
assert part["root2_only_count"] == 15
assert part["root3_only_count"] == 6
assert part["root2_and_root3_count"] == 3

r2 = sorted(part["root2_only"] + part["root2_and_root3"])
r3 = sorted(part["root3_only"] + part["root2_and_root3"])
assert len(r2) == 18 and len(set(r2)) == 18
assert len(r3) == 9 and len(set(r3)) == 9
assert "LIVEBENCH_IF_GE_65_7" not in r2
assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in r3

s = v13["exact_state"]
assert s["accepted_families"] == 5
assert s["open_families"] == 14
assert s["proved_atomic"] == 14
assert s["unresolved_atomic"] == 24
assert s["root1_positive_gap_count"] == 0
assert s["root2_only_count"] == 15
assert s["root3_only_count"] == 6
assert s["root2_and_root3_count"] == 3
assert s["root2_touching_predicates"] == 18
assert s["root3_touching_predicates"] == 9
assert s["exact_root2_only"] == part["root2_only"]
assert s["exact_root3_only"] == part["root3_only"]
assert s["exact_root2_and_root3"] == part["root2_and_root3"]
assert s["exact_root2_touching"] == r2
assert s["exact_root3_touching"] == r3

sb = v13["source_bindings"]
assert sb["terminal_root_state"]["git_blob_sha"] == EXPECTED["ROOT.json"]
assert sb["combined_root_projection"]["git_blob_sha"] == EXPECTED["ROOT.json"]
assert sb["acceptance_ledger_current"]["git_blob_sha"] == EXPECTED["ACCEPTANCE.json"]
assert sb["prior_frontier_v13_pre_rebind"]["git_blob_sha"] == "bb631b80eea5a183728fb27e2aff99bbe63f1757"

epoch = v13["current_epoch"]
assert epoch["acceptance"] == "5/19_PASS__14/19_OPEN"
assert epoch["atomic"] == "14/38_PROVED__24/38_OPEN"
assert epoch["root2_partition"] == "15_ROOT2_ONLY__3_ROOT2_AND_ROOT3__18_TOUCHING"
assert epoch["root3_partition"] == "6_ROOT3_ONLY__3_ROOT2_AND_ROOT3__9_TOUCHING"
assert epoch["root1_positive_gaps"] == 0

assert all(not x.startswith("LIVEBENCH_IF_") for x in v13.get("runnable_zero_reality", []))
assert "LIVEBENCH_IF_BRAIN_SCORE" not in v13.get("fresh_reality_preserved_not_authorized", [])
assert "livebench_if_isolation_route" not in v13

assert v13["execution_authority"] is False
assert v13["promotion_authority"] is False
assert v13["fresh_reality_authority"] is False
assert v13["independent_verification_required"] is True
assert all(x == 0 for x in v13["accounting"].values())

print(json.dumps({
    "status": "PASS",
    "root_blob": EXPECTED["ROOT.json"],
    "acceptance_blob": EXPECTED["ACCEPTANCE.json"],
    "v13_blob": EXPECTED["V13.json"],
    "terminal": False,
    "accepted_families": 5,
    "proved_atomic": 14,
    "unresolved_atomic": 24,
    "root2_touching": 18,
    "root3_touching": 9,
    "fresh_reality_authority": False,
    "acceptance_credit_delta": 0
}, sort_keys=True))
