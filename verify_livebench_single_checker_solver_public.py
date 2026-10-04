#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

BRAIN_COMMIT = "4090f9eb4d50514ca7c4c99470e082c67ffc87ed"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"

SOURCES = {
    "solver": (
        f"https://raw.githubusercontent.com/moxnixmdj/brain/{BRAIN_COMMIT}/canonical/runtime/livebench_if_single_checker_solver_v1.py",
        "b74d986fae033ac94827c5f1eb2db655a99ae4cc",
    ),
    "ngram_dependency": (
        f"https://raw.githubusercontent.com/moxnixmdj/brain/{BRAIN_COMMIT}/canonical/runtime/livebench_ngram_reference_free_v1.py",
        "bcd4a4ede2e70e17e90a33416f3f4a564162f3ea",
    ),
    "ifbench_data": (
        f"https://raw.githubusercontent.com/allenai/IFBench/{IFBENCH_COMMIT}/data/IFBench_test.jsonl",
        "a8e343ed928d8b4e649b9dba651fed7757ccacc3",
    ),
    "instructions": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions.py",
        "02b2dfeb50f036b89bec3df34522c73f756d8f44",
    ),
    "instructions_util": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions_util.py",
        "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
    ),
    "instructions_registry": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions_registry.py",
        "adfed4832877566e62970257b50c6fa32c302fb2",
    ),
    "evaluation_lib": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/evaluation_lib.py",
        "2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
    ),
}

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

raw = {}
for name, (url, expected) in SOURCES.items():
    data = fetch(url)
    observed = git_blob_sha(data)
    assert observed == expected, (name, observed, expected)
    raw[name] = data

for p in [
    Path("canonical"),
    Path("canonical/runtime"),
    Path("livebench"),
    Path("livebench/if_runner"),
    Path("livebench/if_runner/ifbench"),
]:
    p.mkdir(parents=True, exist_ok=True)
    (p / "__init__.py").touch()

Path("canonical/runtime/livebench_if_single_checker_solver_v1.py").write_bytes(raw["solver"])
Path("canonical/runtime/livebench_ngram_reference_free_v1.py").write_bytes(raw["ngram_dependency"])
Path("livebench/if_runner/ifbench/instructions.py").write_bytes(raw["instructions"])
Path("livebench/if_runner/ifbench/instructions_util.py").write_bytes(raw["instructions_util"])
Path("livebench/if_runner/ifbench/instructions_registry.py").write_bytes(raw["instructions_registry"])
Path("livebench/if_runner/ifbench/evaluation_lib.py").write_bytes(raw["evaluation_lib"])

sys.path.insert(0, str(Path.cwd()))

# Reuse the independently preflighted frozen-checker bootstrap. NLTK resources
# must stay local; spaCy is a dead download bootstrap in these exact checker bytes.
import types
import nltk

_RESOURCE_PATHS = {
    "punkt": "tokenizers/punkt",
    "punkt_tab": "tokenizers/punkt_tab",
    "stopwords": "corpora/stopwords",
    "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng": "taggers/averaged_perceptron_tagger_eng",
}
_download_calls = []
def _local_only_download(name, *args, **kwargs):
    _download_calls.append(name)
    path = _RESOURCE_PATHS.get(name)
    if path is None:
        raise RuntimeError("unapproved NLTK resource request: " + str(name))
    nltk.data.find(path)
    return True
nltk.download = _local_only_download

spacy = types.ModuleType("spacy")
spacy.util = types.SimpleNamespace(is_package=lambda _name: True)
spacy_cli = types.ModuleType("spacy.cli")
def _forbidden_spacy_download(*args, **kwargs):
    raise RuntimeError("spaCy network download forbidden")
spacy_cli.download = _forbidden_spacy_download
spacy.cli = spacy_cli
sys.modules["spacy"] = spacy
sys.modules["spacy.cli"] = spacy_cli

from canonical.runtime import livebench_if_single_checker_solver_v1 as solver
from livebench.if_runner.ifbench import evaluation_lib

rows = [json.loads(line) for line in raw["ifbench_data"].decode("utf-8").splitlines() if line.strip()]
assert len(rows) == 300
single = [r for r in rows if len(r.get("instruction_id_list") or []) == 1]

family = defaultdict(lambda: {
    "rows": 0,
    "detected_exactly": 0,
    "candidate_built": 0,
    "exact_checker_pass": 0,
})
failures = []
total_detected = total_built = total_pass = 0

for row in single:
    expected = row["instruction_id_list"][0]
    stat = family[expected]
    stat["rows"] += 1
    out = solver.solve(row["prompt"])
    recognized = list(out.get("recognized_checker_ids") or ([out.get("checker_id")] if out.get("checker_id") else []))
    detected = out.get("checker_id") == expected and out.get("status") == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    if detected:
        stat["detected_exactly"] += 1
        total_detected += 1
    response = out.get("response")
    if detected and isinstance(response, str) and response:
        stat["candidate_built"] += 1
        total_built += 1
        try:
            inp = evaluation_lib.InputExample(
                key=row.get("key"),
                instruction_id_list=list(row["instruction_id_list"]),
                prompt=row["prompt"],
                kwargs=copy.deepcopy(row["kwargs"]),
            )
            result = evaluation_lib.test_instruction_following_strict(inp, response)
            passed = bool(result.follow_all_instructions) and result.follow_instruction_list == [True]
            error = None
        except Exception as exc:
            passed = False
            error = type(exc).__name__ + ":" + str(exc)
        if passed:
            stat["exact_checker_pass"] += 1
            total_pass += 1
        else:
            failures.append({
                "key": row.get("key"),
                "checker_id": expected,
                "phase": "EXACT_CHECKER",
                "error": error,
            })
    else:
        failures.append({
            "key": row.get("key"),
            "checker_id": expected,
            "phase": "DETECT_OR_BUILD",
            "status": out.get("status"),
            "error": out.get("error"),
            "recognized": recognized,
        })

family_out = {k: family[k] for k in sorted(family)}
fully_passing_families = [
    k for k, v in family_out.items()
    if v["rows"] > 0 and v["exact_checker_pass"] == v["rows"]
]
not_fully_passing = [
    k for k, v in family_out.items()
    if v["exact_checker_pass"] != v["rows"]
]

packages = {}
for pkg in ["nltk", "spacy", "emoji", "syllapy", "langdetect", "immutabledict"]:
    try:
        packages[pkg] = importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        packages[pkg] = None

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_SINGLE_CHECKER_SOLVER_PUBLIC_AUDIT_V1",
    "status": "PASS_AUDIT_EXECUTED__NO_TERMINAL_CASES__ZERO_CREDIT",
    "subject": {
        "brain_commit": BRAIN_COMMIT,
        "solver_git_blob_sha": SOURCES["solver"][1],
        "dependency_git_blob_sha": SOURCES["ngram_dependency"][1],
    },
    "frozen_sources": {
        "livebench_commit": LIVEBENCH_COMMIT,
        "ifbench_commit": IFBENCH_COMMIT,
        "git_blobs": {k: v[1] for k, v in SOURCES.items()},
    },
    "population": {
        "public_rows": len(rows),
        "single_checker_rows": len(single),
        "single_checker_families": len(family_out),
    },
    "result": {
        "detected_exactly_rows": total_detected,
        "candidate_built_rows": total_built,
        "exact_checker_pass_rows": total_pass,
        "exact_checker_pass_rate": (total_pass / len(single)) if single else 0.0,
        "fully_passing_family_count": len(fully_passing_families),
        "fully_passing_families": fully_passing_families,
        "not_fully_passing_family_count": len(not_fully_passing),
        "not_fully_passing_families": not_fully_passing,
    },
    "family_results": family_out,
    "failures": failures,
    "environment": {
        "python": sys.version,
        "packages": packages,
    },
    "hard_nonclaims": [
        "PUBLIC_PINNED_IFBENCH_AUDIT_ONLY",
        "NO_UNEXPOSED_TERMINAL_CASE_CONTENT_READ",
        "NO_TERMINAL_POPULATION_EQUIVALENCE_CLAIM",
        "NO_MULTI_CHECKER_COMPOSITION_CLAIM",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
    ],
    "accounting": {
        "incremental_spend_usd": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    },
}
Path("livebench_single_checker_solver_public_audit_receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
