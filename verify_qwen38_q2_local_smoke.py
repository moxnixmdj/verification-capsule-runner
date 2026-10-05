#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys

expected_sha="fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"
out_path=pathlib.Path("qwen38_q2_smoke_output.txt")
meta_path=pathlib.Path("qwen38_q2_smoke_meta.json")
if not out_path.is_file() or not meta_path.is_file():
    raise SystemExit("FAIL_CLOSED:MISSING_SMOKE_ARTIFACT")
text=out_path.read_text(errors="replace").strip()
meta=json.loads(meta_path.read_text())
if meta.get("model_sha256") != expected_sha:
    raise SystemExit("FAIL_CLOSED:MODEL_SHA_MISMATCH")
if meta.get("llama_commit") != "cd26896":
    raise SystemExit("FAIL_CLOSED:LLAMA_COMMIT_MISMATCH")
if len(text) < 20:
    raise SystemExit("FAIL_CLOSED:EMPTY_OR_TRIVIAL_GENERATION")
if "migration" not in text.lower():
    raise SystemExit("FAIL_CLOSED:NONTERMINAL_GROUNDING_TOKEN_MISSING")
receipt={
    "schema":"PROJECT_BRAIN_QWEN38_Q2_LOCAL_CPU_SMOKE_V1",
    "status":"PASS_LOCAL_CPU_LOAD_AND_NONTERMINAL_GENERATION",
    "model":{
        "repository":"unsloth/Qwen3.8-27B-GGUF",
        "file":"Qwen3.8-27B-UD-Q2_K_XL.gguf",
        "bytes":9828981664,
        "sha256":expected_sha,
    },
    "runtime":{
        "repository":"ggml-org/llama.cpp",
        "commit_prefix":"cd26896",
        "version":meta.get("llama_version"),
    },
    "smoke":{
        "context_tokens":2048,
        "max_new_tokens":96,
        "required_grounding_token":"migration",
        "output_chars":len(text),
        "output_excerpt":text[:500],
    },
    "firewall":{
        "terminal_cases_read":0,
        "terminal_content_read":False,
        "acceptance_credit":False,
        "capability_parity_credit":False,
        "incremental_spend_usd":0,
    },
    "hard_nonclaim":"LOAD_AND_ONE_PUBLIC_SYNTHETIC_GENERATION_DO_NOT_PROVE_OPUS_5_5_PARITY_OR_LIVEBENCH_ACCEPTANCE",
}
pathlib.Path("qwen38_q2_smoke_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True))
print("QWEN38_Q2_SMOKE_RECEIPT="+json.dumps(receipt,sort_keys=True))
