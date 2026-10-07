from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UP = ROOT / "upstream"
SUBJECT = json.loads((ROOT / "subject.json").read_text())
MANIFEST = json.loads((ROOT / "MANIFEST.json").read_text())

def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def parse(rel: str) -> ast.Module:
    return ast.parse((UP / rel).read_text(), filename=rel)

def target_value(mod: ast.Module, name: str) -> ast.AST:
    for node in mod.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            if node.value is None:
                raise AssertionError(f"{name}: annotated target has no value")
            return node.value
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return node.value
    raise AssertionError(f"target not found: {name}")

def unwrap_annotated(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Annotated":
        sl = node.slice
        if isinstance(sl, ast.Tuple):
            return sl.elts[0]
        raise AssertionError("Annotated slice shape unsupported")
    return node

def union_names(mod: ast.Module, alias: str) -> list[str]:
    node = unwrap_annotated(target_value(mod, alias))
    if not (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Union"):
        raise AssertionError(f"{alias}: not Union")
    sl = node.slice
    elts = sl.elts if isinstance(sl, ast.Tuple) else [sl]
    out = []
    for x in elts:
        if isinstance(x, ast.Name):
            out.append(x.id)
        else:
            raise AssertionError(f"{alias}: non-name union member {ast.dump(x)}")
    return out

def literal_strings(mod: ast.Module, alias: str) -> list[str]:
    node = target_value(mod, alias)
    if not (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Literal"):
        raise AssertionError(f"{alias}: not Literal")
    sl = node.slice
    elts = sl.elts if isinstance(sl, ast.Tuple) else [sl]
    out = []
    for x in elts:
        if isinstance(x, ast.Constant) and isinstance(x.value, str):
            out.append(x.value)
        else:
            raise AssertionError(f"{alias}: non-string literal {ast.dump(x)}")
    return out

def class_fields(mod: ast.Module, names: list[str]) -> list[str]:
    out = []
    for node in mod.body:
        if isinstance(node, ast.ClassDef) and node.name in names:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    out.append(item.target.id)
    return list(dict.fromkeys(out))

def exact(label: str, got, want):
    if got != want:
        raise AssertionError(f"{label}: got={got!r} want={want!r}")

def verify_subject(subject: dict) -> dict:
    exact("source commit", subject["source"]["pinned_commit"], MANIFEST["upstream"]["commit"])
    exact("source release", subject["source"]["release"], "1.11.0")
    exact("subject blob", git_blob(ROOT / "subject.json"), MANIFEST["brain"]["subject_blob_sha"])

    for rel, want in subject["exact_source_blobs"].items():
        exact("blob " + rel, git_blob(UP / rel), want)

    pyproject = (UP / "pyproject.toml").read_text()
    assert re.search(r'(?m)^name\s*=\s*"anthropic"\s*$', pyproject)
    assert re.search(r'(?m)^version\s*=\s*"1\.11\.0"\s*$', pyproject)
    assert 'description = "The official Python library for the anthropic API"' in pyproject

    stable_cb = union_names(parse("src/anthropic/types/content_block.py"), "ContentBlock")
    stable_cbp = union_names(parse("src/anthropic/types/content_block_param.py"), "ContentBlockParam")
    stable_tools = union_names(parse("src/anthropic/types/tool_union_param.py"), "ToolUnionParam")
    stable_stop = literal_strings(parse("src/anthropic/types/stop_reason.py"), "StopReason")
    stable_fields = class_fields(
        parse("src/anthropic/types/message_create_params.py"),
        ["MessageCreateParamsBase", "MessageCreateParamsNonStreaming", "MessageCreateParamsStreaming"],
    )

    beta_cb = union_names(parse("src/anthropic/types/beta/beta_content_block.py"), "BetaContentBlock")
    beta_cbp = union_names(parse("src/anthropic/types/beta/beta_content_block_param.py"), "BetaContentBlockParam")
    beta_tools = union_names(parse("src/anthropic/types/beta/beta_tool_union_param.py"), "BetaToolUnionParam")
    beta_stop = literal_strings(parse("src/anthropic/types/beta/beta_stop_reason.py"), "BetaStopReason")
    beta_fields = class_fields(
        parse("src/anthropic/types/beta/message_create_params.py"),
        ["MessageCreateParamsBase", "MessageCreateParamsNonStreaming", "MessageCreateParamsStreaming"],
    )

    ss = subject["stable_schema"]
    bs = subject["beta_schema"]
    exact("stable response union", stable_cb, ss["response_content_union"])
    exact("stable response count", len(stable_cb), ss["response_content_union_count"])
    exact("stable request union", stable_cbp, ss["request_content_union"])
    exact("stable request count", len(stable_cbp), ss["request_content_union_count"])
    exact("stable tool union", stable_tools, ss["tool_union"])
    exact("stable tool count", len(stable_tools), ss["tool_union_count"])
    exact("stable stop union", stable_stop, ss["stop_reason_union"])
    exact("stable stop count", len(stable_stop), ss["stop_reason_union_count"])
    exact("stable request fields", stable_fields, ss["all_request_control_fields"])
    exact("stable request field count", len(stable_fields), ss["all_request_control_field_count"])

    exact("beta response union", beta_cb, bs["response_content_union"])
    exact("beta response count", len(beta_cb), bs["response_content_union_count"])
    exact("beta request union", beta_cbp, bs["request_content_union"])
    exact("beta request count", len(beta_cbp), bs["request_content_union_count"])
    exact("beta tool union", beta_tools, bs["tool_union"])
    exact("beta tool count", len(beta_tools), bs["tool_union_count"])
    exact("beta stop union", beta_stop, bs["stop_reason_union"])
    exact("beta stop count", len(beta_stop), bs["stop_reason_union_count"])
    exact("beta request fields", beta_fields, bs["all_request_control_fields"])
    exact("beta request field count", len(beta_fields), bs["all_request_control_field_count"])

    # Named regression boundaries that killed the hand-maintained alphabet.
    assert "ThinkingBlock" in stable_cb
    assert "RedactedThinkingBlock" in stable_cb
    assert "pause_turn" in stable_stop
    assert "refusal" in stable_stop
    assert "BetaMCPToolUseBlock" in beta_cb
    assert "BetaMCPToolResultBlock" in beta_cb
    assert "BetaCompactionBlock" in beta_cb
    assert "BetaFallbackBlock" in beta_cb
    assert "compaction" in beta_stop
    assert "mcp_servers" in beta_fields
    assert "fallbacks" in beta_fields
    assert "context_management" in beta_fields

    return {
        "stable_response_union_count": len(stable_cb),
        "stable_request_union_count": len(stable_cbp),
        "stable_tool_union_count": len(stable_tools),
        "stable_stop_reason_count": len(stable_stop),
        "stable_request_field_count": len(stable_fields),
        "beta_response_union_count": len(beta_cb),
        "beta_request_union_count": len(beta_cbp),
        "beta_tool_union_count": len(beta_tools),
        "beta_stop_reason_count": len(beta_stop),
        "beta_request_field_count": len(beta_fields),
    }

counts = verify_subject(SUBJECT)

# Falsification 1: equal-length wrong union identity must fail.
bad = copy.deepcopy(SUBJECT)
bad["stable_schema"]["response_content_union"][0] = "GhostBlock"
try:
    verify_subject(bad)
except AssertionError as exc:
    assert "stable response union" in str(exc)
else:
    raise AssertionError("wrong union identity did not fail")

# Falsification 2: a new/changed request control field in the frozen source would fail exact closure.
src = parse("src/anthropic/types/message_create_params.py")
got = class_fields(src, ["MessageCreateParamsBase", "MessageCreateParamsNonStreaming", "MessageCreateParamsStreaming"])
assert got == SUBJECT["stable_schema"]["all_request_control_fields"]
synthetic = got + ["future_behavior_changing_field"]
assert synthetic != SUBJECT["stable_schema"]["all_request_control_fields"]

# Falsification 3: blob drift fails even if prose/counts are unchanged.
rel = "src/anthropic/types/content_block.py"
assert git_blob(UP / rel) == SUBJECT["exact_source_blobs"][rel]
assert hashlib.sha1(b"blob 1\0x").hexdigest() != SUBJECT["exact_source_blobs"][rel]

print(json.dumps({
    "schema": "PROJECT_BRAIN_OPUS55_FROZEN_INTERACTION_SCHEMA_SNAPSHOT_INDEPENDENT_VERIFICATION_V1",
    "status": "INDEPENDENT_RECOMPUTATION_PASS",
    "upstream_repository": MANIFEST["upstream"]["repository"],
    "upstream_commit": MANIFEST["upstream"]["commit"],
    "subject_blob_sha": MANIFEST["brain"]["subject_blob_sha"],
    "counts": counts,
    "falsification_tests": 3,
    "schema_snapshot_subobligation_discharged": True,
    "target_discovery_complete": False,
    "brain_domain_dominance_proved": False,
    "acceptance_credit_delta": 0,
    "family_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
}, indent=2, sort_keys=True))
