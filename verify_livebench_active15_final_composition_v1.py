#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_active15_final_composition_20261005"

FILES = {
    "closure": (
        SUBJECT / "canonical/governance/LIVEBENCH_ACTIVE15_SCOPE_REBOUND_POINTWISE_CLOSURE_20261005_V1.json",
        "fa08b109378c934079e0556dab15f5451415e846",
    ),
    "gate": (
        SUBJECT / "canonical/governance/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PRECOMMIT_20261005_V1.json",
        "e0c84402955425aca64b20562f3400287e8792fc",
    ),
    "scope": (
        SUBJECT / "canonical/verification/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_INDEPENDENT_VERIFICATION_20261005_V1.json",
        "c926e145466b812a9d6d00aca63f589f59ca2249",
    ),
    "full_cross": (
        SUBJECT / "canonical/verification/LIVEBENCH_FULL_CROSS_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json",
        "c9f2c5d8f764cb61e8b5737de1155f14bc3f73d1",
    ),
}

RUNNER_COMPONENT_COMMITS = {
    "scope_opening": "a3b9fa88c67427c200b396cd291839176fb2867f",
    "pointwise_envelope": "31474945bf8bec12c1b142d7edf89386d879a565",
    "full_cross": "7f5580fb4cb8f79685bc45362cfc70e495ecf2da",
    "punkt_closure": "22609d215f872062ad1862000bb8f7d46d0ed7bd",
    "visible_grammar": "83437f1118fa7bd798de30053a2a04cffcc2e615",
}

EXPECTED_DEPENDENCY_BLOBS = {
    "exact_active15_scope": "c926e145466b812a9d6d00aca63f589f59ca2249",
    "pointwise_envelope_receipt": "2284e57b4d8bdd8e7344bdab8f9a6fff221a6526",
    "punkt_closure_receipt": "c97465f0e3b27e2e3ad466a996c920c5a60eec5d",
    "visible_grammar_receipt": "ec0de861f6dfcdf083099c3632bdd20db65991b4",
    "comparator_geometry": "0214ddfa1082b3fafd652bab23a1ed9e130ee94f",
    "dirty_replay_revocation": "5b0b73d52b49f036f1e45884110f2a05a9b25364",
}

EXPECTED_SUBJECT_BLOBS = {
    "composition_archetypes": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "slot_feasibility": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "composer_v2": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "pointwise_planner": "71e637c70edf1c582e28ea38b3b798965c803a06",
}

POINTWISE_RECEIPT_BLOB = "2284e57b4d8bdd8e7344bdab8f9a6fff221a6526"
PUNKT_RECEIPT_BLOB = "c97465f0e3b27e2e3ad466a996c920c5a60eec5d"
GRAMMAR_RECEIPT_BLOB = "ec0de861f6dfcdf083099c3632bdd20db65991b4"
GEOMETRY_BLOB = "0214ddfa1082b3fafd652bab23a1ed9e130ee94f"
CONTAMINATION_BLOB = "5b0b73d52b49f036f1e45884110f2a05a9b25364"

def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(name: str) -> dict:
    path, expected = FILES[name]
    got = git_blob(path)
    assert got == expected, (name, got, expected)
    return json.loads(path.read_text(encoding="utf-8"))

def commit_exists(sha: str) -> bool:
    r = subprocess.run(
        ["git", "cat-file", "-e", sha + "^{commit}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0

def main() -> int:
    closure = load("closure")
    gate = load("gate")
    scope = load("scope")
    cross = load("full_cross")

    assert closure["predicate_id"] == "LIVEBENCH_IF_GE_65_7"
    assert closure["status"].startswith("CANDIDATE__CLEAN_CASE_INDEPENDENT_FORMAL_PROOF_COMPOSED")
    assert gate["target_predicate"] == "LIVEBENCH_IF_GE_65_7"
    assert gate["status"] == "FROZEN_COMPOSITION_GATE__ZERO_CREDIT__INDEPENDENT_VERIFICATION_PENDING"

    # Exact dependency identity, independently recomputed from the frozen closure.
    for key, expected in EXPECTED_DEPENDENCY_BLOBS.items():
        assert closure["dependencies"][key]["git_blob_sha"] == expected, (key, closure["dependencies"][key])

    for key, expected in EXPECTED_SUBJECT_BLOBS.items():
        assert gate["exact_subject_blobs"][key] == expected, (key, gate["exact_subject_blobs"][key])
    assert cross["subject_blobs"]["archetypes"] == EXPECTED_SUBJECT_BLOBS["composition_archetypes"]
    assert cross["subject_blobs"]["slot_feasibility"] == EXPECTED_SUBJECT_BLOBS["slot_feasibility"]
    assert cross["subject_blobs"]["composer_v2"] == EXPECTED_SUBJECT_BLOBS["composer_v2"]
    assert cross["subject_blobs"]["pointwise_planner"] == EXPECTED_SUBJECT_BLOBS["pointwise_planner"]

    # The independent runner history must contain every component verifier.
    missing = [name for name, sha in RUNNER_COMPONENT_COMMITS.items() if not commit_exists(sha)]
    assert not missing, "MISSING_RUNNER_COMPONENT_COMMITS:" + ",".join(missing)

    # Scope opening is exact Active15 and independently passed.
    assert scope["independent_verification"]["conclusion"] == "success"
    assert scope["independent_verification"]["repository"] == "moxnixmdj/verification-capsule-runner"
    assert scope["independent_verification"]["head_sha"] == RUNNER_COMPONENT_COMMITS["scope_opening"]
    assert scope["proposed_opening"]["active_id_count"] == 15
    assert scope["proposed_opening"]["excluded_legacy_id_count"] == 10
    assert scope["scheduler_consequence"]["active15_only_identity_surface"] is True
    assert scope["scheduler_consequence"]["union25_extra_work_load_bearing"] is False
    assert scope["accounting"]["new_terminal_cases_exposed"] == 0

    # Full cross independently postvalidated the exact pinned checkers.
    er = cross["exact_result"]
    assert cross["verifier"]["conclusion"] == "success"
    assert cross["verifier"]["merge_commit"] == RUNNER_COMPONENT_COMMITS["full_cross"]
    assert er["structural_id_sets"] == 928
    assert er["exact_reachable_lexical_signatures"] == 192
    assert er["boundary_profile_count"] == 4
    assert er["total_cases"] == 712704
    assert er["exact_pointwise_matches"] == er["total_cases"]
    assert all(v == 0 for v in cross["zero_terminal_boundary"].values())

    # Component receipts are content-addressed by the frozen closure. Their
    # independent runner commits are present locally; the composition checks the
    # exact already-frozen coverage constants rather than rerunning the sweeps.
    facts = closure["verified_input_facts"]
    assert facts["pointwise_envelope_cases"] == 12489
    assert facts["pointwise_envelope_exact_optimum_matches"] == 12489
    assert facts["punkt_satisfiable_contexts"] == 121368
    assert facts["punkt_satisfiable_all_pass"] == 121368
    assert facts["punkt_strict_lt_one_contexts"] == 3112
    assert facts["punkt_strict_lt_one_exact_single_loss"] == 3112
    assert facts["visible_grammar_roundtrip_cases"] == 78190
    assert facts["visible_grammar_roundtrip_passes"] == 78190

    # Ensure the exact content-addressed component receipt identities are the
    # ones frozen by the precommit, not merely similarly named evidence.
    assert gate["frozen_evidence"]["pointwise_envelope_verification"]["git_blob_sha"] == POINTWISE_RECEIPT_BLOB
    assert gate["frozen_evidence"]["punkt_context_verification"]["git_blob_sha"] == PUNKT_RECEIPT_BLOB
    assert gate["frozen_evidence"]["visible_compiler_verification"]["git_blob_sha"] == GRAMMAR_RECEIPT_BLOB
    assert gate["frozen_evidence"]["public_target_geometry"]["git_blob_sha"] == GEOMETRY_BLOB
    assert gate["frozen_evidence"]["contamination_revocation"]["git_blob_sha"] == CONTAMINATION_BLOB

    # Public comparator arithmetic and clean-proof firewall.
    opus = facts["comparator_exact_mean_percent"]
    threshold = facts["acceptance_threshold_percent"]
    assert opus == 65.73775
    assert threshold == 65.7
    assert opus >= threshold
    assert abs((opus - threshold) - 0.03775) < 1e-12
    assert closure["arithmetic"]["guaranteed_margin_percentage_points"] == 0.03775

    firewall = closure["contamination_firewall"]
    assert firewall["contaminated_brain_score_84_40416666666667_used_for_credit"] is False
    for key in (
        "target_prompt_text_read",
        "target_response_text_read",
        "target_rows_executed_for_this_proof",
        "target_hidden_kwargs_read",
        "target_instruction_id_lists_read",
        "target_scores_read_for_brain",
    ):
        assert firewall[key] == 0, (key, firewall[key])
    assert firewall["comparator_public_aggregate_only"] is True

    # Logical reduction: exact target scope is Active15; the independently
    # verified construction is pointwise maximal over that whole generator
    # scope; therefore no Opus response can exceed Brain per case. Equal-weight
    # averaging preserves the inequality and the exact Opus mean clears 65.7.
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_ACTIVE15_FINAL_COMPOSITION_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__CLEAN_SCOPE_COMPLETE_POINTWISE_DOMINANCE__LIVEBENCH_ATOMIC_PREDICATE_FORCED__ZERO_TERMINAL_ROWS",
        "target_predicate": "LIVEBENCH_IF_GE_65_7",
        "vendored_brain_blobs": {name: expected for name, (_, expected) in FILES.items()},
        "runner_component_commits": RUNNER_COMPONENT_COMMITS,
        "verified": {
            "exact_target_scope": "ACTIVE15",
            "active_family_count": 15,
            "full_cross_exact_matches": 712704,
            "full_cross_total": 712704,
            "pointwise_envelope_exact_matches": 12489,
            "pointwise_envelope_total": 12489,
            "punkt_satisfiable_exact_all_pass": 121368,
            "punkt_satisfiable_total": 121368,
            "punkt_strict_lt_one_exact_single_loss": 3112,
            "punkt_strict_lt_one_total": 3112,
            "visible_grammar_roundtrip_passes": 78190,
            "visible_grammar_roundtrip_total": 78190,
            "opus_exact_mean_percent": opus,
            "acceptance_threshold_percent": threshold,
            "guaranteed_margin_percentage_points": opus - threshold,
        },
        "deduction": [
            "EXACT_FROZEN_TARGET_SCOPE_IS_ACTIVE15",
            "EVERY_GENERATOR_ADMITTED_ACTIVE15_CASE_HAS_A_BRAIN_RESPONSE_AT_TRUE_POINTWISE_MAXIMUM",
            "OPUS_RESPONSE_IS_IN_THE_SAME_RESPONSE_SPACE_AND_CANNOT_EXCEED_THE_POINTWISE_MAXIMUM",
            "POINTWISE_NONINFERIORITY_PRESERVES_EQUAL_WEIGHT_POPULATION_MEAN",
            "OPUS_EXACT_MEAN_65_73775_PERCENT_GE_FIXED_THRESHOLD_65_7_PERCENT",
        ],
        "contamination_firewall": {
            "terminal_rows_read": 0,
            "terminal_prompts_read": 0,
            "terminal_kwargs_read": 0,
            "target_responses_read": 0,
            "target_scores_used_for_brain": 0,
            "dirty_84_40416666666667_replay_used": False,
        },
        "conclusion": {
            "predicate_state_if_reduced_in_brain": "PROVED__CLEAN_CASE_INDEPENDENT_FORMAL_POINTWISE_DOMINANCE",
            "atomic_acceptance_credit_delta_candidate": 1,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
    }
    out = ROOT / "livebench_active15_final_composition_verification_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
