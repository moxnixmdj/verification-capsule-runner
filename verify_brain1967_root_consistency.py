import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTH = ROOT / "subjects/brain1967/CURRENT_TERMINAL_AUTHORITY_V1.json"
ROOTS = ROOT / "subjects/brain1967/TERMINAL_ROOT_CAUSE_STATE_V1.json"
EXPECTED_AUTH_BLOB = "95fae2b37a42c0cf1bb2d4b8beba722cd29b0036"
EXPECTED_ROOT_BLOB = "3fd35b7865f7827a5a7b4202bc625fe0f980dcda"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\\0".encode() + data).hexdigest()


def load(path: Path):
    data = path.read_bytes()
    return data, json.loads(data.decode("utf-8"))


def main():
    auth_bytes, authority = load(AUTH)
    root_bytes, roots = load(ROOTS)

    assert git_blob_sha(auth_bytes) == EXPECTED_AUTH_BLOB
    assert git_blob_sha(root_bytes) == EXPECTED_ROOT_BLOB

    partition = roots["current_residual_root_partition"]
    assert partition["root1_positive_gap_count"] == 0
    assert partition["root1_only_count"] == 0
    assert partition["root2_only_count"] == 16
    assert partition["root3_only_count"] == 7
    assert partition["root2_and_root3_count"] == 3
    assert partition["unresolved_total"] == 26
    assert "LIVEBENCH_IF_GE_65_7" in partition["root2_only"]

    expected_touching = partition["root2_only_count"] + partition["root2_and_root3_count"]
    assert expected_touching == 19

    current = authority["current_root_partition_override"]
    assert current["root1_positive_gap_count"] == partition["root1_positive_gap_count"]
    assert current["root1_only"] == partition["root1_only_count"]
    assert current["root2_only"] == partition["root2_only_count"]
    assert current["root3_only"] == partition["root3_only_count"]
    assert current["root2_and_root3"] == partition["root2_and_root3_count"]
    assert current["root2_touching"] == expected_touching
    assert current["unresolved_atomic"] == partition["unresolved_total"]
    assert current["livebench_class"].startswith("ROOT2_ONLY")

    scheduler = authority["root2_current_scheduler_overlay"]
    assert scheduler["effective_touching_predicate_count"] == expected_touching
    assert scheduler["livebench_route"]["state"].startswith("OPEN__ROOT2_ONLY")
    assert scheduler["execution_authority"] is False
    assert scheduler["fresh_reality"] is False

    root_source = authority["sources"]["terminal_root_cause_state_v1"]
    assert root_source["git_blob_sha"] == EXPECTED_ROOT_BLOB

    assert authority["next"] == authority["next_terminal_action"]
    assert "REPAIR_VERIFIED_LIVEBENCH_ROOT1_GAP" not in authority["next"]
    assert "ROOT2_18" not in authority["next"]
    assert "19_ROOT2_TOUCHING_PREDICATES" in authority["next"]
    assert "LIVEBENCH_ROOT1_ONLY" not in authority["rule"]
    assert "ROOT2_EXACTLY_18_TOUCHING" not in authority["rule"]
    assert "ROOT1_ZERO" in authority["rule"]
    assert "ROOT2_EXACTLY_19_TOUCHING" in authority["rule"]

    stale = [
        "post_livebench_current_root_seal",
        "livebench_local_root1_reclassification",
        "root2_post_livebench_18_predicate_rebind",
        "root2_closure_v2_current_frontier",
    ]
    for key in stale:
        assert authority["sources"][key]["effective_scheduling_authority"] is False

    receipt = {
        "schema": "BRAIN_1967_ROOT_CONSISTENCY_INDEPENDENT_VERIFICATION_V1",
        "result": "PASS",
        "authority_git_blob_sha": EXPECTED_AUTH_BLOB,
        "root_git_blob_sha": EXPECTED_ROOT_BLOB,
        "root1_positive_gap_count": 0,
        "root2_touching": expected_touching,
        "livebench_class": "ROOT2_ONLY",
        "terminal_cases_consumed": 0,
        "new_reality_units_consumed": 0,
        "acceptance_credit_delta": 0,
    }
    Path("brain1967_verification_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
