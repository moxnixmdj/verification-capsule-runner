#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACTS = HERE / "PUBLIC_NONTERMINAL_SEMANTIC_CONTRACTS_V1.json"
RECEIPT = HERE / "LIVEBENCH_LOCAL_QWEN_SEMANTIC_SEED_PUBLIC_VERIFICATION_V1.json"

sys.path.insert(0, str(HERE))
from canonical.runtime import local_qwen_semantic_seed_v1 as producer  # noqa: E402


def norm(text: str) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(text or ""))
        .lower()
        .replace("’", "'")
        .split()
    )


def semantic_surface(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", norm(text)))


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w°'-]+\b", unicodedata.normalize("NFKC", text), flags=re.UNICODE))


def sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"[.!?]+(?:\s+|$)", text.strip()) if x.strip()]


def group_pos(text: str, group: list[str], start: int = 0) -> int:
    low = norm(text)
    positions = []
    for alt in group:
        p = low.find(norm(alt), start)
        if p >= 0:
            positions.append(p)
    return min(positions) if positions else -1


def validate(task: dict, output: str) -> tuple[bool, list[str], dict]:
    errors: list[str] = []
    low = norm(output)
    wc = word_count(output)
    metrics = {"word_count": wc}

    if not output.strip():
        errors.append("EMPTY_OUTPUT")

    for i, group in enumerate(task.get("required_groups") or []):
        if group_pos(output, group) < 0:
            errors.append(f"REQUIRED_GROUP_MISSING:{i}:{group}")

    cursor = 0
    for i, group in enumerate(task.get("ordered_groups") or []):
        p = group_pos(output, group, cursor)
        if p < 0:
            errors.append(f"ORDERED_GROUP_MISSING_OR_OUT_OF_ORDER:{i}:{group}")
            break
        cursor = p + 1

    source = task.get("source")
    if task.get("require_nonidentity") and source:
        if semantic_surface(output) == semantic_surface(source):
            errors.append("VERBATIM_OR_SURFACE_IDENTITY")

    if "min_words" in task and wc < int(task["min_words"]):
        errors.append(f"MIN_WORDS:{wc}:{task['min_words']}")
    if "max_words" in task and wc > int(task["max_words"]):
        errors.append(f"MAX_WORDS:{wc}:{task['max_words']}")

    ss = sentences(output)
    metrics["sentence_count"] = len(ss)
    if "sentence_count_min" in task and len(ss) < int(task["sentence_count_min"]):
        errors.append(f"SENTENCE_COUNT_MIN:{len(ss)}:{task['sentence_count_min']}")
    if "sentence_count_max" in task and len(ss) > int(task["sentence_count_max"]):
        errors.append(f"SENTENCE_COUNT_MAX:{len(ss)}:{task['sentence_count_max']}")
    if "max_sentence_words" in task and ss:
        mx = max(word_count(s) for s in ss)
        metrics["max_sentence_words"] = mx
        if mx > int(task["max_sentence_words"]):
            errors.append(f"MAX_SENTENCE_WORDS:{mx}:{task['max_sentence_words']}")

    if "max_source_ratio" in task:
        if not source:
            errors.append("SOURCE_REQUIRED_FOR_RATIO")
        else:
            sw = word_count(source)
            ratio = wc / max(sw, 1)
            metrics["source_word_count"] = sw
            metrics["source_ratio"] = round(ratio, 4)
            if ratio > float(task["max_source_ratio"]):
                errors.append(f"MAX_SOURCE_RATIO:{ratio:.4f}:{task['max_source_ratio']}")

    if low.startswith(("i cannot", "i can't", "as an ai", "here is how", "to do this")):
        errors.append("META_OR_REFUSAL_PREFIX")

    return not errors, errors, metrics


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    tasks = doc.get("tasks") or []
    assert doc.get("schema") == "PROJECT_BRAIN_LIVEBENCH_LOCAL_QWEN_SEMANTIC_CONTRACTS_V1"
    assert len(tasks) == 12
    kinds = [t.get("kind") for t in tasks]
    assert kinds.count("paraphrase") == 3
    assert kinds.count("simplify") == 3
    assert kinds.count("summarize") == 3
    assert kinds.count("story_generation") == 3
    assert doc.get("terminal_cases") == 0

    results = []
    passed = 0
    for task in tasks:
        tid = str(task["id"])
        try:
            generated = producer.generate(str(task["prompt"]), timeout_s=180, max_tokens=512)
            output = str(generated["response"])
            transport_errors = []
            if generated.get("endpoint") != "http://127.0.0.1:8080/v1/chat/completions":
                transport_errors.append("ENDPOINT_NOT_PINNED_LOOPBACK")
            if generated.get("network_scope") != "LOOPBACK_ONLY":
                transport_errors.append("NETWORK_SCOPE_NOT_LOOPBACK_ONLY")
            if generated.get("remote_generation_dependencies") != 0:
                transport_errors.append("REMOTE_GENERATION_DEPENDENCY_NONZERO")
            if generated.get("api_key_dependencies") != 0:
                transport_errors.append("API_KEY_DEPENDENCY_NONZERO")
            if any((generated.get("authority") or {}).values()):
                transport_errors.append("MODEL_AUTHORITY_NONZERO")
            ok, errors, metrics = validate(task, output)
            errors = transport_errors + errors
            ok = ok and not transport_errors
            if ok:
                passed += 1
            results.append({
                "id": tid,
                "kind": task["kind"],
                "status": "PASS" if ok else "FAIL",
                "errors": errors,
                "metrics": metrics,
                "model": generated.get("model"),
                "duration_s": generated.get("duration_s"),
                "output_sha256": sha256_bytes(output.encode("utf-8")),
                "output": output,
            })
        except Exception as exc:
            results.append({
                "id": tid,
                "kind": task.get("kind"),
                "status": "ERROR",
                "errors": [f"{type(exc).__name__}:{exc}"],
            })

    per_kind = {}
    for kind in ("paraphrase", "simplify", "summarize", "story_generation"):
        rows = [x for x in results if x.get("kind") == kind]
        per_kind[kind] = {
            "passed": sum(x.get("status") == "PASS" for x in rows),
            "required": 3,
        }

    full_pass = passed == 12 and all(v["passed"] == v["required"] for v in per_kind.values())
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LOCAL_QWEN_SEMANTIC_SEED_PUBLIC_VERIFICATION_V1",
        "date": "2026-10-04",
        "status": "PASS" if full_pass else "FAIL",
        "subject": {
            "brain_pr": 1742,
            "brain_head": "f53f07a1287ed7c522af432059f33bbad75f1bf8",
            "governance_blob": "aaef67365783f591ea633307c85dd1438add9420",
            "runtime_blob": "5240e0c5651da0539ab58773f89d503cd4959c9d",
            "tests_blob": "2b9bc7d7966b6fe9ec7450668f46828d5590bf3f",
        },
        "pinned_substrate": {
            "llama_cpp_commit": "bec4772f6a2527d371557b5d2032641e5ff7619c",
            "model_file": "Qwen3.5-9B-M-TS-Q4_K_M.gguf",
            "model_bytes": 5060174144,
            "model_sha256": "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
            "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
        },
        "contract_sha256": sha256_bytes(CONTRACTS.read_bytes()),
        "contracts_precommitted_before_generation": True,
        "terminal_cases_consumed": 0,
        "terminal_prompt_or_response_exposure": 0,
        "passed": passed,
        "required": 12,
        "per_kind": per_kind,
        "results": results,
        "verified_consequence_if_pass": [
            "PINNED_LOCAL_QWEN_ROUTE_DEMONSTRATES_PARAPHRASE_SEED_EFFECT_ON_THREE_FROZEN_NONTERMINAL_CONTRACTS",
            "PINNED_LOCAL_QWEN_ROUTE_DEMONSTRATES_SIMPLIFY_SEED_EFFECT_ON_THREE_FROZEN_NONTERMINAL_CONTRACTS",
            "PINNED_LOCAL_QWEN_ROUTE_DEMONSTRATES_SUMMARIZE_SEED_EFFECT_ON_THREE_FROZEN_NONTERMINAL_CONTRACTS",
            "PINNED_LOCAL_QWEN_ROUTE_DEMONSTRATES_STORY_GENERATION_SEED_EFFECT_ON_THREE_FROZEN_NONTERMINAL_CONTRACTS",
            "NEW_MODEL_ACQUISITION_OR_TRAINING_IS_NOT_A_PREREQUISITE_TO_CONTINUE_THE_SEMANTIC_SEED_REPAIR_LANE"
        ] if full_pass else [],
        "hard_nonclaims": [
            "NO_CLAIM_QWEN3_5_9B_EQUALS_OR_EXCEEDS_OPUS_5_5",
            "NO_CLAIM_LIVEBENCH_IF_GE_65_7_IS_CLOSED",
            "NO_CLAIM_TWELVE_SYNTHETIC_CONTRACTS_PROVE_UNIVERSAL_SEMANTIC_EQUIVALENCE",
            "NO_TERMINAL_GENERALIZATION_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_RECEIPT_ALONE"
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0
        }
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "passed": passed,
        "required": 12,
        "per_kind": per_kind,
        "receipt": str(RECEIPT),
    }, sort_keys=True))
    return 0 if full_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
