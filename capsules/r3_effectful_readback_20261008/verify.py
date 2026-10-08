from __future__ import annotations
import ast, hashlib, json, tempfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

for source, meta in M["files"].items():
    p=Path(__file__).resolve().parents[2] / meta["capsule_path"]
    raw=p.read_bytes()
    got=git_blob_sha(raw)
    assert got==meta["git_blob_sha"], (source,got,meta["git_blob_sha"])
    compile(raw, str(p), "exec")

verifier_path=ROOT/"canonical__runtime__r3_independent_learning_verifier_v1.py"
source=verifier_path.read_text(encoding="utf-8")
tree=ast.parse(source)
wanted={"_canon","_sha","_safe_effect_rel","_reverify_effect_outcome"}
body=[]
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name=="R3IndependentVerificationError":
        body.append(node)
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        body.append(node)
assert {x.name for x in body if isinstance(x,ast.FunctionDef)}==wanted
module=ast.Module(body=body,type_ignores=[])

def v1_digest(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

ns={
    "Any":Any,
    "Mapping":Mapping,
    "Sequence":Sequence,
    "Path":Path,
    "PurePosixPath":PurePosixPath,
    "sha256":hashlib.sha256,
    "json":json,
    "VERIFIED_EFFECT_EXECUTOR_ID":"H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
    "VERIFIED_EFFECT_TOOL_IDS":{"JSON_RECEIPT_WRITER_V1","JSONL_LEDGER_APPEND_V1"},
    "v1":SimpleNamespace(_digest=v1_digest),
}
exec(compile(module,str(verifier_path),"exec"),ns)

with tempfile.TemporaryDirectory() as td:
    root=Path(td)/"effect-root"
    sandbox=root/"effect-episode"
    target=sandbox/"receipts"/"result.json"
    target.parent.mkdir(parents=True)
    raw=b'{"name":"Alice","passed":true,"score":0.75}'
    target.write_bytes(raw)
    receipt={
        "op":"WRITE_JSON",
        "path":"receipts/result.json",
        "sha256":hashlib.sha256(raw).hexdigest(),
        "bytes":len(raw),
    }
    outcome={
        "executor_id":"H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
        "tool_id":"JSON_RECEIPT_WRITER_V1",
        "sandbox_rel":"effect-episode",
        "receipts":[receipt],
        "pack_git_blob_sha":"a"*40,
        "prior_verification":"canonical/verification/example.json",
    }
    action={
        "type":"verified_effect_tool",
        "executor_id":"H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
        "executor_payload":{
            "tool_id":"JSON_RECEIPT_WRITER_V1",
            "sandbox_rel":"effect-episode",
        },
    }
    row={
        "effect_outcome":outcome,
        "effect_outcome_sha256":ns["_sha"](outcome),
        "effect_root_sha256":v1_digest(str(root.resolve())),
    }
    ns["_reverify_effect_outcome"](cap={},row=row,action=action,effect_root=root)

    target.write_bytes(raw+b"\n")
    try:
        ns["_reverify_effect_outcome"](cap={},row=row,action=action,effect_root=root)
        raise AssertionError("byte drift was accepted")
    except ns["R3IndependentVerificationError"] as exc:
        assert "READBACK_MISMATCH" in str(exc), exc

    target.write_bytes(raw)
    clone=Path(td)/"clone-root"
    clone_target=clone/"effect-episode"/"receipts"/"result.json"
    clone_target.parent.mkdir(parents=True)
    clone_target.write_bytes(raw)
    try:
        ns["_reverify_effect_outcome"](cap={},row=row,action=action,effect_root=clone)
        raise AssertionError("root substitution was accepted")
    except ns["R3IndependentVerificationError"] as exc:
        assert "EFFECT_ROOT_BINDING_MISMATCH" in str(exc), exc

    try:
        ns["_reverify_effect_outcome"](cap={},row=row,action=action,effect_root=None)
        raise AssertionError("missing root was accepted")
    except ns["R3IndependentVerificationError"] as exc:
        assert "READBACK_ROOT" in str(exc), exc

solver=(ROOT/"canonical__runtime__universal_verified_adaptive_solver_v1.py").read_text()
learning=(ROOT/"canonical__runtime__autonomous_verified_self_improvement_v1.py").read_text()
assert 'completed_record["effect_root_sha256"] = _digest(' in solver
assert 'str(Path(effect_root).resolve())' in solver
assert 'verification_effect_root: str | Path | None = None' in learning
assert '"effect_root": (' in learning
assert 'effect_root=effect_root' in learning

print(json.dumps({
  "status":"PASS",
  "verified":[
    "exact_source_blob_binding",
    "python_compile",
    "matching_effect_readback",
    "one_byte_drift_rejected",
    "matching_bytes_wrong_root_rejected",
    "missing_root_rejected",
    "solver_trace_root_binding_present",
    "r3_effect_root_retention_present"
  ]
},sort_keys=True))
