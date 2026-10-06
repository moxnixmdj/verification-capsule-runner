from __future__ import annotations

import copy
import hashlib
import importlib
import json
import py_compile
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor" / "brain"

EXPECTED = {
    "canonical/runtime/matched_success_semantic_coupling_contract_v3.py":
        "cbb6fc417936ee929ba688b735c17a1b8346c9c7",
    "canonical/governance/MATCHED_SUCCESS_SEMANTIC_COUPLING_CONTRACT_V3.json":
        "d1a86b9d4bd1ff05cd4b57b91d86a393e8b03681",
    "canonical/runtime/matched_success_integrated_extension_v1.py":
        "99da33b4ade3eb4100fdb63d8c7ff98c223afff1",
    "canonical/runtime/matched_success_public_projection_v1.py":
        "52ed0038cd9b7dfc6b3d9c2ca95d69c7d0191e1e",
    "canonical/runtime/matched_success_integrated_causal_harness_v3.py":
        "3df29f5b0abd83077d1853a9c9038dbc599aa5a8",
    "canonical/governance/MATCHED_SUCCESS_INTEGRATED_CAUSAL_HARNESS_V3.json":
        "d8fc9eaba4ad454679b40f1c3db00ec0323f6bf3",
}


def git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def git_blob_sha(path: Path) -> str:
    return git_blob_sha_bytes(path.read_bytes())


def canon(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canon(value)).hexdigest()


def module(name: str, **attrs):
    m = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(m, key, value)
    sys.modules[name] = m
    return m


def generic_case(prefix: str, *args):
    return {
        "public_value": prefix + ":" + ":".join(map(str, args)),
        "public_counter": len(args),
        "private_answer": "HIDDEN_" + prefix,
        "_initial_state": {"page": "start"},
    }


def install_component_stubs() -> None:
    browser_name = "canonical.runtime.browser_state_information_safe_proof"
    module(
        browser_name,
        generate_case=lambda seed, ordinal: generic_case(
            "browser", seed, ordinal
        ),
        public_state=lambda case, state, history: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
            "page": state.get("page"),
            "history_len": len(history),
        },
    )

    d3_name = "canonical.runtime.delegation_structural_variety_proof_v3"
    module(
        d3_name,
        generate_case=lambda seed, ordinal: generic_case(
            "delegation_v3", seed, ordinal
        ),
        public_case=lambda case: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
        },
    )

    d2_name = "canonical.runtime.delegation_whole_scope_proof_v2"
    module(
        d2_name,
        generate_case=lambda seed, ordinal: generic_case(
            "delegation_v2", seed, ordinal
        ),
        public_initial=lambda case: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
        },
    )

    tool_name = "canonical.runtime.tool_discovery_information_safe_proof_v2"
    module(
        tool_name,
        generate_case=lambda seed, ordinal: generic_case(
            "tool", seed, ordinal
        ),
        public_stage=lambda case, stage, prior: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
            "stage": stage,
            "prior_count": len(tuple(prior)),
        },
    )

    m0_name = "canonical.runtime.m0a_raw_source_terminal_suite_v2"
    module(
        m0_name,
        generate_case=lambda seed, ordinal: generic_case(
            "m0", seed, ordinal
        ),
        public_task=lambda case: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
        },
    )

    contract_name = "canonical.runtime.contract_native_proof_suites"
    module(
        contract_name,
        generate_case=lambda behavior, seed, ordinal: generic_case(
            "contract:" + str(behavior), seed, ordinal
        ),
        public_task=lambda case: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
        },
    )

    native_name = "canonical.runtime.native_artifact_cross_format_proof_v1"
    module(
        native_name,
        FORMATS=("docx", "xlsx"),
        generate_case=lambda fmt, seed: generic_case(
            "native:" + str(fmt), seed
        ),
        public_task=lambda case: {
            "public_value": case["public_value"],
            "public_counter": case["public_counter"],
        },
    )

    scope_name = "canonical.runtime.matched_success_scope_compiler_v1"
    module(
        scope_name,
        INPUT_SCHEMA="PROJECT_BRAIN_MATCHED_SUCCESS_SCOPE_INPUT_V1",
    )


def text(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


class ConnectedAgent:
    def __init__(self):
        self.memory = None

    def __call__(self, kind, public, context):
        if kind == "semantic_capture":
            self.memory = public["source_value"]
            return {
                "captured_value": public["source_value"],
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "semantic_tool_transform":
            return {
                "derived_value": "tool::" + text(public["input_value"]),
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "semantic_delegate_and_recall":
            return {
                "recalled_value": self.memory,
                "final_value": (
                    "delegate::"
                    + str(public["derived_value"])
                    + "::"
                    + text(self.memory)
                ),
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind in {"instruction_initial", "instruction_changed"}:
            c = public["constraints"]
            return {
                "output": c["prefix"] + text(public["value"]) + c["suffix"]
            }
        if kind == "semantic_synthesis":
            return {
                "synthesis": "SYNTH::" + text(public["upstream_value"])
            }
        if kind == "semantic_artifact":
            return {
                "artifact": "ARTIFACT[" + str(public["synthesis"]) + "]"
            }
        if kind == "memory_write":
            self.memory = public["value"]
            return {"stored": True}
        if kind == "browser_recovery":
            return {"recovered": True, "recalled_value": self.memory}
        if kind == "debug_failure":
            return {
                "root_cause": (
                    "required_value_mismatch"
                    if (
                        public["mutated"]["required_value"]
                        != public["expected_required_value"]
                    )
                    else "none"
                )
            }
        if kind == "discover_repair_tool":
            return {
                "tool": (
                    "semantic_value_restorer"
                    if public["root_cause"] == "required_value_mismatch"
                    else "unrelated_formatter"
                )
            }
        if kind == "apply_repair":
            if public["tool"] != "semantic_value_restorer":
                return {"repaired": public["mutated"]}
            return {
                "repaired": {
                    "required_value": public["required_value"],
                    "status": "correct",
                }
            }
        if kind == "rollback_decision":
            return {"rollback": True}
        raise AssertionError(kind)


class DisconnectedAgent(ConnectedAgent):
    def __call__(self, kind, public, context):
        if kind == "semantic_tool_transform":
            return {
                "derived_value": "tool::DISCONNECTED",
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "instruction_changed":
            c = public["constraints"]
            return {
                "output": c["prefix"] + "DISCONNECTED" + c["suffix"]
            }
        if kind == "semantic_synthesis":
            return {"synthesis": "SYNTH::DISCONNECTED"}
        if kind == "semantic_artifact":
            return {"artifact": "ARTIFACT[SYNTH::DISCONNECTED]"}
        if kind == "memory_write":
            self.memory = "DISCONNECTED"
            return {"stored": True}
        if kind == "debug_failure":
            return {"root_cause": "none"}
        if kind == "rollback_decision":
            return {"rollback": False}
        return super().__call__(kind, public, context)


def verify_receipt_pack(bundle) -> None:
    docs = bundle["receipt_documents"]
    certificate = bundle["certificate"]
    receipts = []
    for row in certificate["classes"]:
        for role in ("true", "ablated", "rescue"):
            run = row[role + "_run"]
            semantic_record = {
                "class_id": row["class_id"],
                "run_role": role,
                "upstream_semantic_sha256":
                    run["upstream_semantic_sha256"],
                "upstream_shape_sha256":
                    run["upstream_shape_sha256"],
                "terminal_semantic_sha256":
                    run["terminal_semantic_sha256"],
                "success": run["success"],
            }
            assert run["run_semantics_sha256"] == digest(semantic_record)
            receipts.append(run["receipt"])

        assert row["details_sha256"] == digest(row["details"])
        receipts.append(row["details_receipt"])

    assert len(receipts) == 28
    assert len(docs) == 28

    for receipt in receipts:
        data = docs[receipt["path"]].encode("utf-8")
        assert git_blob_sha_bytes(data) == receipt["git_blob_sha"]
        body = json.loads(data)
        for key, value in body.items():
            assert receipt[key] == value
        assert body["independent_or_objective"] is True


def main() -> None:
    for rel, expected in EXPECTED.items():
        actual = git_blob_sha(VENDOR / rel)
        assert actual == expected, (rel, actual, expected)

    for rel in (
        "canonical/runtime/matched_success_semantic_coupling_contract_v3.py",
        "canonical/runtime/matched_success_integrated_extension_v1.py",
        "canonical/runtime/matched_success_public_projection_v1.py",
        "canonical/runtime/matched_success_integrated_causal_harness_v3.py",
    ):
        py_compile.compile(str(VENDOR / rel), doraise=True)

    contract_gov = json.loads(
        (
            VENDOR
            / "canonical/governance/MATCHED_SUCCESS_SEMANTIC_COUPLING_CONTRACT_V3.json"
        ).read_text()
    )
    harness_gov = json.loads(
        (
            VENDOR
            / "canonical/governance/MATCHED_SUCCESS_INTEGRATED_CAUSAL_HARNESS_V3.json"
        ).read_text()
    )
    for gov in (contract_gov, harness_gov):
        assert gov["execution_authority"] is False
        assert gov["promotion_authority"] is False
        assert gov["fresh_reality_authority"] is False
        assert gov["acceptance_credit_delta"] == 0
        assert gov["capability_credit_delta"] == 0
        assert gov["ownership_credit_delta"] == 0

    sys.path.insert(0, str(VENDOR))
    import canonical.runtime  # noqa: F401
    install_component_stubs()

    contract = importlib.import_module(
        "canonical.runtime.matched_success_semantic_coupling_contract_v3"
    )
    generator = importlib.import_module(
        "canonical.runtime.matched_success_integrated_extension_v1"
    )
    projection = importlib.import_module(
        "canonical.runtime.matched_success_public_projection_v1"
    )
    harness = importlib.import_module(
        "canonical.runtime.matched_success_integrated_causal_harness_v3"
    )

    bundle = harness.build_v3_bundle(
        "INDEPENDENT_V3_REHEARSAL_COMMITMENT",
        "INDEPENDENT_V3_REHEARSAL_BEACON",
        ConnectedAgent,
    )
    out = contract.compile_coupling_v3(bundle["certificate"])
    assert out["status"] == (
        "PASS__CONTENT_BOUND_INTERVENTIONAL_SEMANTIC_COUPLING_V3"
    )
    assert out["class_count"] == 7
    assert out["independent_receipt_bytes_verified"] is False
    assert bundle["terminal_case_generation"] is False
    assert bundle["fresh_reality_consumed"] == 0
    verify_receipt_pack(bundle)

    bad = harness.build_v3_bundle(
        "INDEPENDENT_V3_BAD_COMMITMENT",
        "INDEPENDENT_V3_BAD_BEACON",
        DisconnectedAgent,
    )
    bad_out = contract.compile_coupling_v3(bad["certificate"])
    assert bad_out["status"] == "FAIL_CLOSED"

    # Public-only information boundary: add a raw hidden sentinel that the
    # projection deliberately omits, then prove the selected source is public.
    atom = harness.CLASS_ATOM["RESEARCH_TOOL_ARTIFACT"]
    case = generator.generate_case(
        atom, 0, "PUBLIC_BOUNDARY_C", "PUBLIC_BOUNDARY_B"
    )
    first = case["case_payload"]["payload"]["components"][0]
    first["case"]["HIDDEN_SENTINEL_DO_NOT_USE"] = "SECRET_ORACLE_VALUE"
    public = projection.public_component(first)
    public_values = [
        value for _, value in harness._scalar_leaves(public)
    ]
    assert "SECRET_ORACLE_VALUE" not in public_values
    source = harness._semantic_source(case)
    assert source in public_values
    assert source != "SECRET_ORACLE_VALUE"

    # A receipt-byte substitution must be independently visible even though
    # the V3 runtime itself only sees the bound hash/reference fields.
    tampered = copy.deepcopy(bundle)
    any_path = sorted(tampered["receipt_documents"])[0]
    tampered["receipt_documents"][any_path] = (
        tampered["receipt_documents"][any_path].rstrip()
        + " "
        + "\n"
    )
    try:
        verify_receipt_pack(tampered)
    except AssertionError:
        tamper_rejected = True
    else:
        tamper_rejected = False
    assert tamper_rejected is True

    print(json.dumps({
        "status": "PASS",
        "exact_brain_blob_count": len(EXPECTED),
        "runtime_py_compile_pass": True,
        "v3_connected_bundle_pass": True,
        "v3_disconnected_bundle_rejected": True,
        "exact_receipt_document_count": 28,
        "receipt_byte_substitution_rejected": True,
        "public_only_semantic_source_verified": True,
        "terminal_case_generation": False,
        "fresh_reality_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
