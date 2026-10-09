from __future__ import annotations

from canonical.runtime import harbor_science_agent_v9 as agent


def candidate(action_id, covers, *, depends_on=None, command="printf ok", verify_command="true"):
    return {
        "action_id": action_id,
        "covers": covers,
        "depends_on": list(depends_on or []),
        "command": command,
        "verify_command": verify_command,
    }


def test_unknown_cover_is_local_rejection_and_valid_siblings_survive():
    rows, rejected = agent._candidate_rows(
        [
            candidate("r1", ["R1"]),
            # Forbidden command is deliberate: coverage rejection must happen
            # before command validation and the candidate must never execute.
            candidate("bad", ["R1", "X"], command="curl https://example.invalid"),
            candidate("blocked_by_bad", ["R2"], depends_on=["bad"]),
            candidate("r2", ["R2"], depends_on=["r1"]),
        ],
        {"R1", "R2"},
    )
    assert [row["action_id"] for row in rows] == ["r1", "r2"], rows
    assert all(row["executable"] is False for row in rejected)
    assert all(row["promotable"] is False for row in rejected)

    by_id = {row["action_id"]: row for row in rejected}
    assert by_id["bad"]["reason"] == "COVERAGE_OUTSIDE_FROZEN_CONTRACT"
    assert by_id["bad"]["unknown_covers"] == ["X"]
    assert by_id["bad"]["covers"] == ["R1", "X"]
    assert by_id["blocked_by_bad"]["reason"] == "DEPENDS_ON_REJECTED_OR_UNKNOWN_ACTION"
    assert by_id["blocked_by_bad"]["unavailable_dependencies"] == ["bad"]


def test_dependency_rejection_closes_transitively():
    rows, rejected = agent._candidate_rows(
        [
            candidate("bad", ["X"]),
            candidate("d1", ["R1"], depends_on=["bad"]),
            candidate("d2", ["R2"], depends_on=["d1"]),
            candidate("good", ["R1"]),
        ],
        {"R1", "R2"},
    )
    assert [row["action_id"] for row in rows] == ["good"], rows
    by_id = {row["action_id"]: row for row in rejected}
    assert by_id["bad"]["reason"] == "COVERAGE_OUTSIDE_FROZEN_CONTRACT"
    assert by_id["d1"]["reason"] == "DEPENDS_ON_REJECTED_OR_UNKNOWN_ACTION"
    assert by_id["d2"]["reason"] == "DEPENDS_ON_REJECTED_OR_UNKNOWN_ACTION"


def test_candidate_local_command_failure_does_not_abort_valid_sibling():
    rows, rejected = agent._candidate_rows(
        [
            candidate("badcmd", ["R1"], command="wget https://example.invalid"),
            candidate("good", ["R2"]),
        ],
        {"R1", "R2"},
    )
    assert [row["action_id"] for row in rows] == ["good"]
    assert rejected[0]["action_id"] == "badcmd"
    assert rejected[0]["reason"] == "CANDIDATE_FIELD_OR_COMMAND_INVALID"


def test_frozen_requirement_set_survives_multi_cycle_substrate_drift():
    raw0 = {
        "material_requirements": ["R1", "R2"],
        "candidates": [candidate("first", ["R1"])],
    }
    requirements, rows, summary, rejected = agent._extract_contract(raw0, None, [])
    assert requirements == ["R1", "R2"]
    assert [row["action_id"] for row in rows] == ["first"]
    assert summary is None
    assert rejected == []

    raw1 = {
        # Post-freeze substrate requirements are metadata only.
        "material_requirements": ["EVIL"],
        "candidates": [
            candidate("outside", ["EVIL"]),
            candidate("second", ["R2"]),
        ],
    }
    requirements1, rows1, summary1, rejected1 = agent._extract_contract(
        raw1, requirements, []
    )
    assert requirements1 == ["R1", "R2"]
    assert [row["action_id"] for row in rows1] == ["second"]
    assert summary1 is None
    assert rejected1[0]["action_id"] == "outside"
    assert rejected1[0]["reason"] == "COVERAGE_OUTSIDE_FROZEN_CONTRACT"
    assert rejected1[0]["unknown_covers"] == ["EVIL"]

    # A later cycle remains usable after the malformed optional proposal.
    raw2 = {
        "material_requirements": ["DIFFERENT"],
        "candidates": [candidate("third", ["R1"])],
    }
    requirements2, rows2, _, rejected2 = agent._extract_contract(
        raw2, requirements1, []
    )
    assert requirements2 == ["R1", "R2"]
    assert [row["action_id"] for row in rows2] == ["third"]
    assert rejected2 == []


def test_unknown_coverage_is_never_coerced_into_frozen_coverage():
    rows, rejected = agent._candidate_rows(
        [candidate("mixed", ["R1", "X"])],
        {"R1"},
    )
    assert rows == []
    assert rejected == [{
        "kind": "PLANNER_CANDIDATE_REJECTED",
        "candidate_index": 0,
        "action_id": "mixed",
        "reason": "COVERAGE_OUTSIDE_FROZEN_CONTRACT",
        "executable": False,
        "promotable": False,
        "covers": ["R1", "X"],
        "unknown_covers": ["X"],
    }]


def main():
    tests = [
        test_unknown_cover_is_local_rejection_and_valid_siblings_survive,
        test_dependency_rejection_closes_transitively,
        test_candidate_local_command_failure_does_not_abort_valid_sibling,
        test_frozen_requirement_set_survives_multi_cycle_substrate_drift,
        test_unknown_coverage_is_never_coerced_into_frozen_coverage,
    ]
    for fn in tests:
        fn()
    print(f"PASS__TB_SCIENCE_CANDIDATE_LOCAL_REJECTION__{len(tests)}_OF_{len(tests)}")


if __name__ == "__main__":
    main()
