#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
import string
import urllib.request
from collections import Counter, defaultdict

BASE = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/"
DATA_URL = BASE + "data/IFBench_test.jsonl"
INST_URL = BASE + "ifbench/instructions.py"
REG_URL = BASE + "ifbench/instructions_registry.py"
EXPECTED = {
    DATA_URL: "a8e343ed928d8b4e649b9dba651fed7757ccacc3",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-public-surface-analysis"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def registry_map(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if not any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in node.targets):
                continue
            if not isinstance(node.value, ast.Dict):
                continue
            for k, v in zip(node.value.keys, node.value.values):
                if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
                    continue
                if isinstance(v, ast.Attribute):
                    out[k.value] = v.attr
    return out


def expr_template(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = expr_template(node.left), expr_template(node.right)
        return None if a is None or b is None else a + b
    if isinstance(node, ast.JoinedStr):
        parts = []
        for x in node.values:
            if isinstance(x, ast.Constant) and isinstance(x.value, str):
                parts.append(x.value)
            elif isinstance(x, ast.FormattedValue):
                if isinstance(x.value, ast.Name):
                    parts.append("{" + x.value.id + "}")
                elif isinstance(x.value, ast.Attribute):
                    parts.append("{" + x.value.attr + "}")
                else:
                    parts.append("{VALUE}")
            else:
                return None
        return "".join(parts)
    return None


def class_templates(source: str) -> dict[str, list[str]]:
    tree = ast.parse(source)
    out: dict[str, list[str]] = defaultdict(list)
    for cls in [x for x in tree.body if isinstance(x, ast.ClassDef)]:
        for node in ast.walk(cls):
            if not isinstance(node, ast.Assign):
                continue
            hit = False
            for t in node.targets:
                if isinstance(t, ast.Attribute) and t.attr == "_description_pattern":
                    hit = True
            if not hit:
                continue
            s = expr_template(node.value)
            if s and s not in out[cls.name]:
                out[cls.name].append(s)
    return dict(out)


def template_regex(template: str) -> re.Pattern:
    parts = []
    for literal, field, spec, conv in string.Formatter().parse(template):
        if literal:
            chunks = re.split(r"(\s+)", literal)
            for ch in chunks:
                if not ch:
                    continue
                parts.append(r"\s+" if ch.isspace() else re.escape(ch))
        if field is not None:
            # Non-greedy captures bounded by the surrounding public template text.
            parts.append(r".+?")
    return re.compile("".join(parts), re.I | re.S)


def main() -> int:
    raw = fetch(DATA_URL)
    inst_raw = fetch(INST_URL)
    reg_raw = fetch(REG_URL)
    assert blob(raw) == EXPECTED[DATA_URL]

    rows = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    reg = registry_map(reg_raw.decode())
    templates = class_templates(inst_raw.decode())

    patterns: dict[str, list[re.Pattern]] = {}
    template_counts = {}
    no_template = []
    for iid, cls in reg.items():
        ts = templates.get(cls, [])
        template_counts[iid] = len(ts)
        if not ts:
            no_template.append(iid)
        patterns[iid] = [template_regex(t) for t in ts]

    exact_rows = 0
    subset_rows = 0
    missed = Counter()
    extras = Counter()
    examples = []
    for row in rows:
        prompt = str(row.get("prompt") or "")
        expected_ids = list(row.get("instruction_id_list") or [])
        found = sorted(iid for iid, ps in patterns.items() if any(p.search(prompt) for p in ps))
        expected = sorted(expected_ids)
        if found == expected:
            exact_rows += 1
        if set(expected).issubset(found):
            subset_rows += 1
        for x in set(expected) - set(found):
            missed[x] += 1
        for x in set(found) - set(expected):
            extras[x] += 1
        if found != expected and len(examples) < 12:
            examples.append({"expected": expected, "found": found})

    result = {
        "schema": "PROJECT_BRAIN_IFBENCH_PUBLIC_PROMPT_SURFACE_RECOGNIZER_ANALYSIS_V1",
        "source": {
            "ifbench_commit": "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d",
            "data_git_blob_sha": blob(raw),
            "instructions_git_blob_sha": blob(inst_raw),
            "registry_git_blob_sha": blob(reg_raw),
        },
        "row_count": len(rows),
        "registry_instruction_count": len(reg),
        "classes_with_extracted_templates": sum(bool(templates.get(cls)) for cls in set(reg.values())),
        "ids_without_extracted_template": sorted(no_template),
        "exact_hidden_id_recovery_rows": exact_rows,
        "hidden_ids_subset_of_recognized_rows": subset_rows,
        "missed_instruction_counts": dict(missed.most_common()),
        "false_positive_instruction_counts": dict(extras.most_common()),
        "mismatch_examples": examples,
        "network_used_for_public_source_fetch_only": True,
        "terminal_cases_consumed": 0,
        "conclusion": "PASS" if exact_rows == len(rows) else "RECOGNIZER_NEEDS_REPAIR",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
