from __future__ import annotations

import ast
import hashlib
import itertools
import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor" / "brain"

EXPECTED = {
    "canonical/runtime/matched_success_semantic_coupling_contract_v2.py":
        "67510185451397a41c7aa5d445490e02fec4af3d",
    "canonical/governance/MATCHED_SUCCESS_SEMANTIC_COUPLING_CONTRACT_V2.json":
        "a7bfd67cd554e21373b798779556d92ceb1e9662",
    "canonical/runtime/matched_success_integrated_causal_harness_v2.py":
        "4f099166fcbe2a79a693f3385b24efc9d6235d00",
    "canonical/governance/MATCHED_SUCCESS_INTEGRATED_CAUSAL_HARNESS_V2.json":
        "a0da79a9cd88db916d0b05bb9515ac8ef399307e",
    "canonical/tests/test_matched_success_semantic_coupling_contract_v2.py":
        "01ea746cbc39b6f9155f5b6a14757945364bbbd6",
    "canonical/tests/test_matched_success_integrated_causal_harness_v2.py":
        "d02dc3020b4b83df23de3fc374dda3f454f8381e",
}

REQUIRED_CLASSES = {
    "AGENCY_THREE_TOOL_LONG_HORIZON",
    "INSTRUCTION_CHANGE_CONTROL",
    "RESEARCH_TOOL_ARTIFACT",
    "BROWSER_MEMORY_RECOVERY",
    "CODING_DEBUG_TOOL_DISCOVERY",
    "DELEGATION_SYNTHESIS_ARTIFACT",
    "CROSS_CAPABILITY_HANDOFF_ROLLBACK",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def load(rel: str):
    return json.loads((VENDOR / rel).read_text(encoding="utf-8"))


def independent_contract_accepts(
    *,
    true_up: int,
    decoy_up: int,
    rescue_up: int,
    true_success: bool,
    decoy_success: bool,
    rescue_success: bool,
    true_terminal: int,
    rescue_terminal: int,
) -> bool:
    return (
        true_up != decoy_up
        and rescue_up == true_up
        and true_success is True
        and decoy_success is False
        and rescue_success is True
        and rescue_terminal == true_terminal
    )


def main() -> None:
    for rel, expected in EXPECTED.items():
        actual = git_blob_sha(VENDOR / rel)
        assert actual == expected, (rel, actual, expected)

    runtime_files = [
        VENDOR / "canonical/runtime/matched_success_semantic_coupling_contract_v2.py",
        VENDOR / "canonical/runtime/matched_success_integrated_causal_harness_v2.py",
    ]
    for path in runtime_files:
        py_compile.compile(str(path), doraise=True)

    contract_gov = load(
        "canonical/governance/MATCHED_SUCCESS_SEMANTIC_COUPLING_CONTRACT_V2.json"
    )
    harness_gov = load(
        "canonical/governance/MATCHED_SUCCESS_INTEGRATED_CAUSAL_HARNESS_V2.json"
    )

    assert set(contract_gov["required_classes"]) == REQUIRED_CLASSES
    rule = contract_gov["universal_intervention_rule"]
    assert rule["true_upstream_run_must_pass"] is True
    assert rule["same_shape_semantic_decoy_run_must_fail"] is True
    assert rule["restored_true_upstream_run_must_pass"] is True
    assert rule["true_and_rescue_terminal_semantics_must_match"] is True
    assert rule["decoy_must_differ_semantically_from_true_upstream"] is True
    assert rule["mere_receipt_or_hash_acknowledgement_is_not_sufficient"] is True

    for gov in (contract_gov, harness_gov):
        assert gov["execution_authority"] is False
        assert gov["promotion_authority"] is False
        assert gov["fresh_reality_authority"] is False
        assert gov["acceptance_credit_delta"] == 0
        assert gov["capability_credit_delta"] == 0
        assert gov["ownership_credit_delta"] == 0

    contract_src = runtime_files[0].read_text(encoding="utf-8")
    harness_src = runtime_files[1].read_text(encoding="utf-8")
    contract_ast = ast.parse(contract_src)
    harness_ast = ast.parse(harness_src)

    contract_functions = {
        n.name for n in ast.walk(contract_ast)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    harness_functions = {
        n.name for n in ast.walk(harness_ast)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "compile_coupling" in contract_functions
    assert "_intervention" in contract_functions
    assert "run_class" in harness_functions
    assert "build_coupling_certificate" in harness_functions
    assert "_run_rollback" in harness_functions
    assert "_decoy" in harness_functions

    for token in (
        "DECOY_NOT_SEMANTICALLY_DISTINCT",
        "RESCUE_UPSTREAM_NOT_RESTORED",
        "RESCUE_TERMINAL_NOT_RESTORED",
        "MUTATION_DID_NOT_CHANGE_STATE",
        "ROLLBACK_DID_NOT_RESTORE_STATE",
    ):
        assert token in contract_src

    for token in (
        'intervention == "decoy"',
        "transported == source",
        "post_sha == checkpoint",
        "STALE_STATE_AFTER_NAVIGATION",
        "semantic_value_restorer",
    ):
        assert token in harness_src

    # Independent exhaustive miniature model check of the V2 intervention law.
    accepted = 0
    for (
        true_up,
        decoy_up,
        rescue_up,
        true_success,
        decoy_success,
        rescue_success,
        true_terminal,
        rescue_terminal,
    ) in itertools.product(
        range(2), range(2), range(2),
        (False, True), (False, True), (False, True),
        range(2), range(2),
    ):
        ok = independent_contract_accepts(
            true_up=true_up,
            decoy_up=decoy_up,
            rescue_up=rescue_up,
            true_success=true_success,
            decoy_success=decoy_success,
            rescue_success=rescue_success,
            true_terminal=true_terminal,
            rescue_terminal=rescue_terminal,
        )
        if ok:
            accepted += 1
            assert true_up != decoy_up
            assert rescue_up == true_up
            assert true_success
            assert not decoy_success
            assert rescue_success
            assert rescue_terminal == true_terminal

    assert accepted > 0

    # The precise V1 failure mode must be rejected: an acknowledgement-only
    # decoy that still "passes" cannot satisfy the V2 law.
    assert not independent_contract_accepts(
        true_up=0,
        decoy_up=1,
        rescue_up=0,
        true_success=True,
        decoy_success=True,
        rescue_success=True,
        true_terminal=0,
        rescue_terminal=0,
    )

    # Rescue that fails to restore terminal semantics must also be rejected.
    assert not independent_contract_accepts(
        true_up=0,
        decoy_up=1,
        rescue_up=0,
        true_success=True,
        decoy_success=False,
        rescue_success=True,
        true_terminal=0,
        rescue_terminal=1,
    )

    print(json.dumps({
        "status": "PASS",
        "exact_vendored_blob_count": len(EXPECTED),
        "runtime_py_compile_pass": True,
        "required_class_count": len(REQUIRED_CLASSES),
        "independent_finite_model_accepted_states": accepted,
        "ack_only_false_positive_rejected": True,
        "bad_rescue_rejected": True,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
