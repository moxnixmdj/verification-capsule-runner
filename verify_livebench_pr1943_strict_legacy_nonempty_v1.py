#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import pathlib
import tempfile
import urllib.request

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as subject

EXPECTED_BRAIN_BLOBS = {
  "canonical/runtime/livebench_legacy15_exact_postvalidator_v1.py": "5f6ca08c85df67a460323816c2bf74c88cf1fc90",
  "canonical/runtime/livebench_legacy15_exact_contract_checker_v1.py": "39d282529087f7c2390a1035f2fa152ded7f0343",
  "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
}
LB_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM = {
    "instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "evaluation_main.py": "4a341984936c4d609644a3b77f8c030ac5aa7269",
}

def git_blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def git_blob_path(path: str) -> str:
    return git_blob_bytes(pathlib.Path(path).read_bytes())

for path, expected in EXPECTED_BRAIN_BLOBS.items():
    got = git_blob_path(path)
    assert got == expected, (path, got, expected)

assert subject.PINNED_LIVEBENCH_COMMIT == LB_COMMIT
assert subject.PINNED_EVALUATION_MAIN_BLOB == UPSTREAM["evaluation_main.py"]

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    package = root / "livebench" / "if_runner" / "instruction_following_eval"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")

    fetched = {}
    for name, expected in UPSTREAM.items():
        url = (
            "https://raw.githubusercontent.com/LiveBench/LiveBench/"
            + LB_COMMIT
            + "/livebench/if_runner/instruction_following_eval/"
            + name
        )
        raw = urllib.request.urlopen(url, timeout=30).read()
        got = git_blob_bytes(raw)
        assert got == expected, (name, got, expected)
        (package / name).write_bytes(raw)
        fetched[name] = raw

    source = fetched["evaluation_main.py"].decode("utf-8")
    exact_rule = "if response.strip() and instruction.check_following(response):"
    assert exact_rule in source

    registry, binding = subject.load_pinned_registry(root)
    assert binding["evaluation_main_blob"] == UPSTREAM["evaluation_main.py"]
    assert binding["strict_nonempty_guard"].startswith("response.strip()")
    assert "keywords:forbidden_words" in registry

    contract = {
        "instruction_id": "keywords:forbidden_words",
        "slots": {"forbidden_words": ["omega"]},
        "parameter_complete": True,
    }
    raw_checker = registry["keywords:forbidden_words"]("keywords:forbidden_words")
    raw_checker.build_description(forbidden_words=["omega"])
    assert raw_checker.check_following("") is True

    blank = subject.evaluate_with_registry("", [contract], registry)
    spaces = subject.evaluate_with_registry(" \n\t ", [contract], registry)
    nonblank = subject.evaluate_with_registry("0", [contract], registry)

    assert blank["checker_results"] == [False]
    assert spaces["checker_results"] == [False]
    assert nonblank["checker_results"] == [True]
    assert blank["strict_nonempty_guard_applied"] is True
    assert blank["response_nonempty"] is False
    assert nonblank["response_nonempty"] is True

print("LIVEBENCH_PR1943_STRICT_LEGACY_NONEMPTY_VERIFICATION=PASS")
print("brain_runtime_blob=" + EXPECTED_BRAIN_BLOBS["canonical/runtime/livebench_legacy15_exact_postvalidator_v1.py"])
print("legacy_evaluation_main_blob=" + UPSTREAM["evaluation_main.py"])
print("active_terminal_rows_read=0")
print("hidden_kwargs_read=0")
print("incremental_spend_usd=0")
