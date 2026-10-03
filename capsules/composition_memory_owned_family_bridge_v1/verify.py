from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

FILES = {
    "binding": "canonical/governance/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V1.json",
    "envelope": "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
    "protocols": "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
    "manifest": "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json",
    "memory": "canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json",
}
EXPECTED_BLOBS = {
    FILES["binding"]: "d073b395c3ec335e5aebe45e100a8a9a345905f6",
    FILES["envelope"]: "661a57f839101fbf54c7e4edc76166c65ce9327d",
    FILES["protocols"]: "eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
    FILES["manifest"]: "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    FILES["memory"]: "2d912cf8df64bd806fffb6a1070d95644d005470",
}
GENERAL_SEMANTIC_EXCLUSION = "GENERAL_SEMANTIC_MEMORY_QUALITY_OR_RECALL_ACCURACY"
CLAIM = "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
INTERFACE = "browser/computer action+memory+recovery"
MEMORY_FAMILY = "LONG_HORIZON_MEMORY_AND_CONTINUITY"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def verify(binding, envelope, protocols, manifest, memory) -> list[str]:
    errors: list[str] = []

    families = envelope.get("families", [])
    if len(families) != 19:
        errors.append("TERMINAL_FAMILY_COUNT_NOT_19")

    composition_rows = [x for x in families if x.get("id") == "MULTI_CAPABILITY_COMPOSITION"]
    memory_rows = [x for x in families if x.get("id") == MEMORY_FAMILY]
    if len(composition_rows) != 1 or len(memory_rows) != 1:
        errors.append("CANONICAL_FAMILY_ROWS_NOT_UNIQUE")
    else:
        if not re.search(r"\bmemory\b", composition_rows[0].get("useful_behavior", ""), re.I):
            errors.append("COMPOSITION_ENVELOPE_DOES_NOT_LITERALIZE_MEMORY")
        if not re.search(r"\bmemory\b", memory_rows[0].get("useful_behavior", ""), re.I):
            errors.append("MEMORY_FAMILY_ENVELOPE_DOES_NOT_LITERALIZE_MEMORY")

    non_composition_memory_rows = [
        x for x in families
        if x.get("id") != "MULTI_CAPABILITY_COMPOSITION"
        and re.search(r"\bmemory\b", x.get("useful_behavior", ""), re.I)
    ]
    if [x.get("id") for x in non_composition_memory_rows] != [MEMORY_FAMILY]:
        errors.append("CLOSED_WORLD_MEMORY_ROLE_NOT_UNIQUE")

    protocol_rows = protocols.get("protocols", [])
    comp_protocol = [x for x in protocol_rows if x.get("family") == "MULTI_CAPABILITY_COMPOSITION"]
    mem_protocol = [x for x in protocol_rows if x.get("family") == MEMORY_FAMILY]
    if len(comp_protocol) != 1 or len(mem_protocol) != 1:
        errors.append("PROTOCOL_ROWS_NOT_UNIQUE")
    else:
        if INTERFACE not in comp_protocol[0].get("task_dimensions", []):
            errors.append("FROZEN_COMPOSITION_MEMORY_INTERFACE_MISSING")
        if mem_protocol[0].get("status") != "PASS":
            errors.append("MEMORY_TERMINAL_PROTOCOL_NOT_PASS")

    mem_interfaces = [
        x for x in manifest.get("interfaces", [])
        if x.get("component_id") == "memory"
    ]
    if len(mem_interfaces) != 1:
        errors.append("FROZEN_MEMORY_COMPONENT_NOT_UNIQUE")
    elif mem_interfaces[0].get("interface_id") != INTERFACE:
        errors.append("FROZEN_MEMORY_INTERFACE_CHANGED")

    if memory.get("family") != MEMORY_FAMILY:
        errors.append("OWNERSHIP_PACKAGE_FAMILY_MISMATCH")
    if memory.get("status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
        errors.append("OWNERSHIP_PACKAGE_NOT_VERIFIED_OWNED")
    decision = memory.get("decision", {})
    if decision.get("parent_family_closed_for_claim_scope") is not True:
        errors.append("MEMORY_PARENT_FAMILY_NOT_CLOSED")
    if decision.get("global_memory_superiority_claim") is not False:
        errors.append("GLOBAL_MEMORY_SUPERIORITY_MUST_REMAIN_FALSE")

    package_excluded = set(memory.get("excluded_scope", []))
    bridge_guard = binding.get("scope_guard", {})
    binding_excluded = set(bridge_guard.get("excluded_scope", []))
    if package_excluded != binding_excluded:
        errors.append("SOURCE_EXCLUDED_SCOPE_NOT_PRESERVED_EXACTLY")
    if GENERAL_SEMANTIC_EXCLUSION not in binding_excluded:
        errors.append("GENERAL_SEMANTIC_MEMORY_EXCLUSION_MISSING")
    if bridge_guard.get("included_scope") != memory.get("claim_scope"):
        errors.append("BINDING_SCOPE_NOT_EXACT_SOURCE_CLAIM_SCOPE")

    cb = binding.get("component_binding", {})
    if cb.get("component_id") != "memory" or cb.get("interface_id") != INTERFACE:
        errors.append("BINDING_COMPONENT_OR_INTERFACE_MISMATCH")
    if cb.get("proved_properties_after_independent_verification") != ["SCOPED_ACCEPTANCE_PROOF"]:
        errors.append("BINDING_PROOF_PROPERTY_INVALID")

    receipt = binding.get("candidate_receipt", {})
    if receipt.get("component_id") != "memory" or receipt.get("interface_id") != INTERFACE:
        errors.append("CANDIDATE_RECEIPT_BINDING_INVALID")
    if receipt.get("binds_frozen_claim") != CLAIM:
        errors.append("CANDIDATE_RECEIPT_CLAIM_INVALID")
    if receipt.get("source_family") != MEMORY_FAMILY:
        errors.append("CANDIDATE_RECEIPT_SOURCE_FAMILY_INVALID")
    if receipt.get("verified") is not False or receipt.get("independent") is not False:
        errors.append("CANDIDATE_PRETENDS_PREVERIFIED")
    if receipt.get("acceptance_scoped") is not True or receipt.get("contamination_clean") is not True:
        errors.append("CANDIDATE_SCOPE_OR_CONTAMINATION_FLAG_INVALID")

    authority = binding.get("authority", {})
    expected_authorities = {
        "terminal_envelope": (FILES["envelope"], EXPECTED_BLOBS[FILES["envelope"]]),
        "terminal_protocols": (FILES["protocols"], EXPECTED_BLOBS[FILES["protocols"]]),
        "composition_manifest": (FILES["manifest"], EXPECTED_BLOBS[FILES["manifest"]]),
        "owned_memory_package": (FILES["memory"], EXPECTED_BLOBS[FILES["memory"]]),
    }
    for key, (path, sha) in expected_authorities.items():
        row = authority.get(key, {})
        if row.get("path") != path or row.get("git_blob_sha") != sha:
            errors.append(f"AUTHORITY_BINDING_INVALID:{key}")

    for field in (
        "new_reality_units_consumed",
        "incremental_spend_usd",
        "capability_credit_delta",
        "family_credit_delta",
    ):
        if binding.get(field) != 0:
            errors.append(f"NONZERO_FORBIDDEN:{field}")
    if binding.get("execution_authority") is not False or binding.get("promotion_authority") is not False:
        errors.append("CANDIDATE_AUTHORITY_MUST_BE_FALSE")

    return errors


def main() -> int:
    for rel, expected in EXPECTED_BLOBS.items():
        actual = git_blob_sha((ROOT / rel).read_bytes())
        if actual != expected:
            print(json.dumps({"status": "FAIL", "error": "BLOB_MISMATCH", "path": rel, "expected": expected, "actual": actual}))
            return 1

    docs = {key: load(rel) for key, rel in FILES.items()}
    errors = verify(
        docs["binding"], docs["envelope"], docs["protocols"], docs["manifest"], docs["memory"]
    )
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1

    # Adversarial: a second terminal family claiming a memory role destroys uniqueness.
    bad_envelope = copy.deepcopy(docs["envelope"])
    bad_envelope["families"].insert(
        0,
        {"id": "ADVERSARIAL_SECOND_MEMORY_FAMILY", "useful_behavior": "Use memory for arbitrary recall."},
    )
    if "CLOSED_WORLD_MEMORY_ROLE_NOT_UNIQUE" not in verify(
        docs["binding"], bad_envelope, docs["protocols"], docs["manifest"], docs["memory"]
    ):
        print(json.dumps({"status": "FAIL", "error": "ADVERSARIAL_DUPLICATE_MEMORY_ROLE_ACCEPTED"}))
        return 1

    # Adversarial: removing the semantic-memory exclusion must fail.
    bad_binding = copy.deepcopy(docs["binding"])
    bad_binding["scope_guard"]["excluded_scope"].remove(GENERAL_SEMANTIC_EXCLUSION)
    if "SOURCE_EXCLUDED_SCOPE_NOT_PRESERVED_EXACTLY" not in verify(
        bad_binding, docs["envelope"], docs["protocols"], docs["manifest"], docs["memory"]
    ):
        print(json.dumps({"status": "FAIL", "error": "ADVERSARIAL_SCOPE_BROADENING_ACCEPTED"}))
        return 1

    # Adversarial: moving the receipt to another interface must fail.
    bad_binding2 = copy.deepcopy(docs["binding"])
    bad_binding2["candidate_receipt"]["interface_id"] = "coding+debugging+tool discovery"
    if "CANDIDATE_RECEIPT_BINDING_INVALID" not in verify(
        bad_binding2, docs["envelope"], docs["protocols"], docs["manifest"], docs["memory"]
    ):
        print(json.dumps({"status": "FAIL", "error": "ADVERSARIAL_INTERFACE_REBIND_ACCEPTED"}))
        return 1

    print(json.dumps({
        "status": "PASS",
        "verified": [
            "EXACT_FIVE_BRAIN_BLOBS",
            "CLOSED_WORLD_19_FAMILY_ENVELOPE",
            "UNIQUE_NON_COMPOSITION_TERMINAL_MEMORY_ROLE",
            "FROZEN_MEMORY_COMPONENT_AND_INTERFACE",
            "MEMORY_TERMINAL_PROTOCOL_PASS",
            "VERIFIED_OWNED_EQUAL_OR_BETTER_MEMORY_PACKAGE",
            "EXACT_SOURCE_CLAIM_SCOPE",
            "GENERAL_SEMANTIC_MEMORY_EXCLUSION_PRESERVED",
            "ZERO_CREDIT_ZERO_AUTHORITY",
            "ADVERSARIAL_DUPLICATE_MEMORY_ROLE_REJECTED",
            "ADVERSARIAL_SCOPE_BROADENING_REJECTED",
            "ADVERSARIAL_INTERFACE_REBIND_REJECTED"
        ],
        "effect": "AUTHORIZES_ONLY_MEMORY_COMPONENT_SCOPED_ACCEPTANCE_RECEIPT_PROMOTION_INTO_COMPOSITION_SLICER_INPUT"
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
