#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, importlib, json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject/public_description_inverter_v1"
RUNTIME = SUB / "canonical/runtime/public_description_template_inverter_v1.py"
TESTS = SUB / "canonical/tests/test_public_description_template_inverter_v1.py"
BRAIN_BLOBS = {
    "runtime": "ec958baa0cb6ad8ece4b69437b88abbcbea5994e",
    "tests": "2a87383de2f2ebf0b9c73ad544f9a4324475650f",
}
UPSTREAM_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM = {
    "modern_source": ("livebench/if_runner/ifbench/instructions.py", "02b2dfeb50f036b89bec3df34522c73f756d8f44"),
    "modern_registry": ("livebench/if_runner/ifbench/instructions_registry.py", "adfed4832877566e62970257b50c6fa32c302fb2"),
    "legacy_source": ("livebench/if_runner/instruction_following_eval/instructions.py", "4997bab885a676d92545fd91a9a20b48d234a2b2"),
    "legacy_registry": ("livebench/if_runner/instruction_following_eval/instructions_registry.py", "903ed738398648c7cfac61d5ffa478c22f1f0891"),
}

def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def fetch(rel: str, expected: str) -> str:
    url = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/{rel}"
    data = urllib.request.urlopen(url, timeout=30).read()
    got = git_blob_bytes(data)
    assert got == expected, (rel, got, expected)
    return data.decode("utf-8")

assert git_blob_bytes(RUNTIME.read_bytes()) == BRAIN_BLOBS["runtime"]
assert git_blob_bytes(TESTS.read_bytes()) == BRAIN_BLOBS["tests"]

sys.path.insert(0, str(SUB))
inv = importlib.import_module("canonical.runtime.public_description_template_inverter_v1")

# Run all candidate tests without requiring pytest.
spec = importlib.util.spec_from_file_location("candidate_tests", TESTS)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
test_names = sorted(x for x in dir(mod) if x.startswith("test_"))
assert len(test_names) == 6, test_names
for name in test_names:
    getattr(mod, name)()

sources = {name: fetch(path, blob) for name, (path, blob) in UPSTREAM.items()}

def active_classes(registry_source: str) -> set[str]:
    tree = ast.parse(registry_source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in node.targets):
            assert isinstance(node.value, ast.Dict)
            out = set()
            for value in node.value.values:
                if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == "instructions":
                    out.add(value.attr)
                else:
                    raise AssertionError(("UNEXPECTED_REGISTRY_VALUE", ast.dump(value)))
            return out
    raise AssertionError("INSTRUCTION_DICT_NOT_FOUND")

modern_active = active_classes(sources["modern_registry"])
legacy_active = active_classes(sources["legacy_registry"])
assert len(modern_active) == 58, len(modern_active)
assert len(legacy_active) == 25, len(legacy_active)

modern_audit = inv.audit(sources["modern_source"], expected_classes=modern_active)
legacy_audit = inv.audit(sources["legacy_source"], expected_classes=legacy_active)
assert modern_audit["all_expected_classes_covered"], modern_audit["missing_expected_classes"]
assert legacy_audit["all_expected_classes_covered"], legacy_audit["missing_expected_classes"]

# Exact real-public-template round trip on a rendered parameter.
modern_specs = inv.extract_templates(sources["modern_source"])
hits = inv.match_prompt(
    "Synthetic base request. Use at least 17 unique words in the response.",
    modern_specs,
)
unique_hits = [x for x in hits if x["class_name"] == "UniqueWordCountChecker"]
assert len(unique_hits) == 1, unique_hits
assert unique_hits[0]["parameters"]["N"] == "17"

receipt = {
    "schema": "PROJECT_BRAIN_PUBLIC_DESCRIPTION_TEMPLATE_INVERTER_V1_INDEPENDENT_VERIFICATION",
    "status": "PASS",
    "brain_pr": 1727,
    "brain_head": "1f3578a7ee4e56cecada8447db4e98a898ed4d59",
    "exact_brain_blobs": BRAIN_BLOBS,
    "upstream_commit": UPSTREAM_COMMIT,
    "upstream_blobs": {k: v[1] for k, v in UPSTREAM.items()},
    "candidate_tests_executed": test_names,
    "verified": {
        "source_execution": False,
        "modern_active_instruction_types": len(modern_active),
        "modern_active_description_coverage": len(modern_active) - len(modern_audit["missing_expected_classes"]),
        "legacy_active_instruction_types": len(legacy_active),
        "legacy_active_description_coverage": len(legacy_active) - len(legacy_audit["missing_expected_classes"]),
        "modern_all_active_covered": modern_audit["all_expected_classes_covered"],
        "legacy_all_active_covered": legacy_audit["all_expected_classes_covered"],
        "real_public_parameter_round_trip": True,
    },
    "terminal_cases_consumed": 0,
    "acceptance_credit_delta": 0,
    "incremental_spend_usd": 0,
}
(ROOT / "public_description_inverter_v1_receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
