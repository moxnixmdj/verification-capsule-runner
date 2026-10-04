#!/usr/bin/env python3
"""Sanitized diagnostic replay for the already-exposed LiveBench V6 72-case prefix.

This program MUST NOT persist or print prompt text, response text, raw stdout,
raw stderr, traceback text, or arbitrary exception messages. It emits only:
- already-exposed question IDs,
- process exit/status classes,
- SHA-256 and byte length of hidden stderr/response bytes,
- error-code tokens derived solely from the frozen runtime source,
- exception-class names derived from source plus a fixed safe builtin set.

It grants no new-case, acceptance, promotion, capability, or Root1 authority.
"""
from __future__ import annotations

import ast
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import shutil
from collections import Counter

ROOT=pathlib.Path(__file__).resolve().parent
ORIGINAL=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_ORIGINAL_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
REPLAY_LIMIT=72
SAFE_BUILTIN_EXCEPTION_CLASSES={
    "Blocker","RuntimeError","ValueError","TypeError","KeyError","IndexError",
    "AssertionError","ImportError","ModuleNotFoundError","FileNotFoundError",
    "PermissionError","TimeoutError","SystemExit","JSONDecodeError",
    "LiveBenchPostPromptAcquisitionForbidden",
}
ERROR_TOKEN_RE=re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")
CLASS_TOKEN_RE=re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Blocker)\b")

def git_blob_sha(path:pathlib.Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

if git_blob_sha(ORIGINAL)!=EXPECTED_ORIGINAL_BLOB:
    raise SystemExit("FAIL_CLOSED:ORIGINAL_EXECUTOR_BLOB_DRIFT")

spec=importlib.util.spec_from_file_location("livebench_v6_executor",ORIGINAL)
if not spec or not spec.loader:
    raise SystemExit("FAIL_CLOSED:ORIGINAL_EXECUTOR_IMPORT_SPEC")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def _source_string_literals(path:pathlib.Path):
    try:
        tree=ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [
        node.value for node in ast.walk(tree)
        if isinstance(node,ast.Constant) and isinstance(node.value,str)
    ]

def build_source_allowlist(template:pathlib.Path)->tuple[set[str],set[str]]:
    """Build privacy-safe diagnostic vocabulary only from frozen source bytes."""
    codes:set[str]=set()
    classes=set(SAFE_BUILTIN_EXCEPTION_CLASSES)
    runtime=template/"canonical"/"runtime"
    for path in sorted(runtime.rglob("*.py")):
        for literal in _source_string_literals(path):
            for token in ERROR_TOKEN_RE.findall(literal):
                if "_" in token:
                    codes.add(token)
            for cls in CLASS_TOKEN_RE.findall(literal):
                classes.add(cls)
        try:
            tree=ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node,ast.ClassDef) and (
                node.name.endswith("Error")
                or node.name.endswith("Exception")
                or node.name.endswith("Blocker")
            ):
                classes.add(node.name)
    # These two policy classes live in the fixed CASE_DRIVER rather than a file.
    codes.update(ERROR_TOKEN_RE.findall(m.CASE_DRIVER))
    classes.update(CLASS_TOKEN_RE.findall(m.CASE_DRIVER))
    return codes,classes

def sanitize_hidden_text(text:str,allowed_codes:set[str],allowed_classes:set[str])->dict:
    raw=str(text or "")
    encoded=raw.encode("utf-8","replace")
    observed_codes=set(ERROR_TOKEN_RE.findall(raw))
    observed_classes=set(CLASS_TOKEN_RE.findall(raw))
    return {
        "sha256":hashlib.sha256(encoded).hexdigest(),
        "bytes":len(encoded),
        "source_error_codes":sorted(observed_codes & allowed_codes)[:64],
        "source_exception_classes":sorted(observed_classes & allowed_classes)[:32],
    }

def infer_one_sanitized(
    template:pathlib.Path,
    q:dict,
    allowed_codes:set[str],
    allowed_classes:set[str],
)->dict:
    qid=str(q["question_id"])
    with tempfile.TemporaryDirectory(prefix="lb-diag-case-") as td:
        case=pathlib.Path(td)
        shutil.copytree(template,case/"root",dirs_exist_ok=True)
        root=case/"root"
        env=os.environ.copy()
        env["PYTHONPATH"]=str(root)
        req={
            "benchmark_id":m.BENCHMARK_ID,
            "task_id":qid,
            "task_payload":{"instruction":q["turns"][0]},
            "allowed_tools":[],
        }
        try:
            cp=subprocess.run(
                [sys.executable,"-c",m.CASE_DRIVER],
                input=json.dumps(req),
                text=True,
                capture_output=True,
                cwd=root,
                env=env,
                timeout=45,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "question_id":qid,
                "kind":"TIMEOUT",
                "timeout_seconds":45,
                "hidden_input_sha256":hashlib.sha256(
                    json.dumps(req,sort_keys=True).encode()
                ).hexdigest(),
                "exception_class":"TimeoutExpired",
            }
        except Exception as exc:
            # Never serialize str(exc): it can contain terminal content.
            return {
                "question_id":qid,
                "kind":"DIAGNOSTIC_WRAPPER_EXCEPTION",
                "exception_class":type(exc).__name__
                    if type(exc).__name__ in allowed_classes else "UNCLASSIFIED_EXCEPTION",
            }

        if cp.returncode!=0:
            safe=sanitize_hidden_text(cp.stderr,allowed_codes,allowed_classes)
            return {
                "question_id":qid,
                "kind":"INFERENCE_EXIT",
                "exit_code":int(cp.returncode),
                "stderr_sha256":safe["sha256"],
                "stderr_bytes":safe["bytes"],
                "source_error_codes":safe["source_error_codes"],
                "source_exception_classes":safe["source_exception_classes"],
            }

        stdout=str(cp.stdout or "")
        stdout_sha=hashlib.sha256(stdout.encode("utf-8","replace")).hexdigest()
        try:
            out=json.loads(stdout)
        except Exception:
            return {
                "question_id":qid,
                "kind":"OUTPUT_JSON_INVALID",
                "stdout_sha256":stdout_sha,
                "stdout_bytes":len(stdout.encode("utf-8","replace")),
            }

        status=str(out.get("status") or "")
        if status=="BLOCKED__POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN":
            return {
                "question_id":qid,
                "kind":"POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION",
                "status_sha256":hashlib.sha256(status.encode()).hexdigest(),
            }
        if status=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE":
            answer=str(out.get("answer") or "")
            return {
                "question_id":qid,
                "kind":"VALID_CANDIDATE_RESPONSE",
                "response_sha256":hashlib.sha256(answer.encode()).hexdigest(),
                "response_bytes":len(answer.encode("utf-8","replace")),
            }
        # Never print arbitrary status text. Only source-derived tokens escape.
        safe=sanitize_hidden_text(status,allowed_codes,allowed_classes)
        return {
            "question_id":qid,
            "kind":"OTHER_INFERENCE_STATUS",
            "status_sha256":safe["sha256"],
            "source_error_codes":safe["source_error_codes"],
        }

def diagnostic_signature(rec:dict)->str:
    payload={
        "kind":rec.get("kind"),
        "exit_code":rec.get("exit_code"),
        "source_error_codes":rec.get("source_error_codes",[]),
        "source_exception_classes":rec.get("source_exception_classes",[]),
    }
    return json.dumps(payload,sort_keys=True,separators=(",",":"))

def main(*,authorized:bool=False,activation_blob:str|None=None)->int:
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:SANITIZED_DIAGNOSTIC_AUTHORITY_REQUIRED")
    if not isinstance(activation_blob,str) or re.fullmatch(r"[0-9a-f]{40}",activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:SANITIZED_DIAGNOSTIC_ACTIVATION_BLOB_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS")!="true" or str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    if sys.version_info[:2]!=(3,12):
        raise SystemExit("FAIL_CLOSED:PYTHON_3_12_REQUIRED")

    # Recheck exact frozen runtime bytes before any benchmark case is read.
    for _,(rel,expected) in m.RUNTIME_FILES.items():
        p=ROOT/rel
        if not p.is_file() or m.git_blob_sha(p)!=expected:
            raise SystemExit("FAIL_CLOSED:RUNTIME_COMPONENT_DRIFT:"+rel)

    with tempfile.TemporaryDirectory(prefix="livebench-sanitized-diagnostic-") as td:
        base=pathlib.Path(td)
        # Preserve the same point-of-use environment setup as the V6 replay.
        m.install_scorer_deps()
        m.prepare_nltk(base)
        m.clone_livebench(base)
        parquet=m.download_dataset(base)
        questions=m.parse_population(base,parquet)
        if len(questions)!=200:
            raise SystemExit("FAIL_CLOSED:POPULATION_COUNT_MISMATCH")
        template=m.build_runtime_template(base)
        allowed_codes,allowed_classes=build_source_allowlist(template)
        if not allowed_codes:
            raise SystemExit("FAIL_CLOSED:EMPTY_SOURCE_ERROR_ALLOWLIST")

        receipts=[]
        for start in range(0,REPLAY_LIMIT,m.BATCH):
            batch=questions[start:min(start+m.BATCH,REPLAY_LIMIT)]
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(len(batch),os.cpu_count() or 2)
            ) as ex:
                raw=list(ex.map(
                    lambda q: infer_one_sanitized(
                        template,q,allowed_codes,allowed_classes
                    ),
                    batch,
                ))
            by_id={x["question_id"]:x for x in raw}
            for q in batch:
                rec=by_id[str(q["question_id"])]
                receipts.append(rec)
                print(
                    "LIVEBENCH_SANITIZED_BLOCKER_RECEIPT="
                    +json.dumps(rec,sort_keys=True,separators=(",",":")),
                    flush=True,
                )

        if len(receipts)!=72 or len({x["question_id"] for x in receipts})!=72:
            raise SystemExit("FAIL_CLOSED:DIAGNOSTIC_PREFIX_IDENTITY_MISMATCH")

        kinds=Counter(x["kind"] for x in receipts)
        signatures=Counter(diagnostic_signature(x) for x in receipts)
        summary={
            "schema":"PROJECT_BRAIN_LIVEBENCH_V6_SANITIZED_BLOCKER_DIAGNOSTIC_RESULT_V1",
            "status":"DIAGNOSTIC_COMPLETE__ZERO_CREDIT",
            "activation_blob_sha":activation_blob,
            "replayed_already_exposed_case_count":72,
            "new_case_exposure_count":0,
            "prefix_limit":72,
            "unique_question_ids":72,
            "kind_counts":dict(sorted(kinds.items())),
            "diagnostic_signature_counts":[
                {"signature":json.loads(sig),"count":count}
                for sig,count in sorted(signatures.items())
            ],
            "source_error_allowlist_sha256":hashlib.sha256(
                "\n".join(sorted(allowed_codes)).encode()
            ).hexdigest(),
            "source_error_allowlist_count":len(allowed_codes),
            "raw_prompt_persisted":False,
            "raw_response_persisted":False,
            "raw_stdout_persisted":False,
            "raw_stderr_persisted":False,
            "incremental_spend_usd":0,
            "acceptance_credit_delta":0,
            "promotion_authority":False,
            "root1_reclassification_authority":False,
        }
        print(
            "LIVEBENCH_SANITIZED_DIAGNOSTIC_RESULT="
            +json.dumps(summary,sort_keys=True,separators=(",",":")),
            flush=True,
        )
    return 0

if __name__=="__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_SANITIZED_DIAGNOSTIC_LAUNCHER_REQUIRED")
