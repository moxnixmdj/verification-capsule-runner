#!/usr/bin/env python3
from __future__ import annotations

import collections
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
BASE_EXEC = ROOT / "execute_livebench_if_replay72_v4_candidate.py"
EXPECTED = {
    "execute_livebench_if_replay72_v4_candidate.py": "2a57ce896ddbd6819246aab8b44d17a00f36b61e",
    "canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py": "dbc895a0e458e411aafd3c96e0ddc2c01e657375",
    "canonical/runtime/root2_livebench_if_astra_inference_adapter_v3.py": "ff977b2e34d551e5a2751852bb77d23c7c503647",
    "canonical/runtime/instruction_constraint_compiler_v1.py": "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}
REPLAY_LIMIT = 72
BATCH = 8

CASE_DRIVER = r'''
import hashlib,json,sys

def _audit(event,args):
    if event=="socket.connect":
        raise RuntimeError("LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN")
    if event=="subprocess.Popen":
        exe=args[0] if len(args)>0 else ""
        argv=args[1] if len(args)>1 else ()
        parts=[str(exe)]
        if isinstance(argv,(list,tuple)): parts.extend(str(x) for x in argv)
        else: parts.append(str(argv))
        text=" "+" ".join(parts).lower()
        forbidden=(
            " pip install"," -m pip install"," npm install"," npm i ",
            " apt-get install"," apt install"," git clone"," curl "," wget "
        )
        if any(tok in text for tok in forbidden):
            raise RuntimeError("LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN")
sys.addaudithook(_audit)

from canonical.runtime import astra_runtime
class LiveBenchPostPromptAcquisitionForbidden(RuntimeError): pass
def _deny_auto_capability_acquisition():
    raise LiveBenchPostPromptAcquisitionForbidden(
        "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN"
    )
astra_runtime._load_auto_capability_acquisition=_deny_auto_capability_acquisition

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as adapter
req=json.loads(sys.stdin.read())
try:
    out=adapter.infer(req)
except Exception as exc:
    msg=type(exc).__name__+":"+str(exc)
    policy=(
        "CAPABILITY_ACQUISITION_REQUIRED" in msg or
        "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN" in msg or
        "LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN" in msg or
        "LiveBenchPostPromptAcquisitionForbidden" in msg
    )
    out={
        "status":"BLOCKED__POLICY" if policy else "BLOCKED__OTHER",
        "answer":"",
        "response_route":"",
        "error_digest":hashlib.sha256(msg.encode()).hexdigest(),
    }
print(json.dumps({
    "status":out.get("status"),
    "answer":str(out.get("answer") or ""),
    "response_route":str(out.get("response_route") or ""),
},sort_keys=True))
'''


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_base():
    for rel, expected in EXPECTED.items():
        p = ROOT / rel
        if not p.is_file() or git_blob_sha(p) != expected:
            raise RuntimeError("SUBJECT_BLOB_DRIFT:" + rel)
    spec = importlib.util.spec_from_file_location("livebench_v11_base", BASE_EXEC)
    if spec is None or spec.loader is None:
        raise RuntimeError("BASE_EXECUTOR_IMPORT_SPEC")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mod.REPLAY_LIMIT != 72 or mod.POPULATION != 200:
        raise RuntimeError("BASE_EXECUTOR_SCOPE_DRIFT")
    return mod


def build_template(base: pathlib.Path, mod) -> pathlib.Path:
    template = mod.build_runtime_template(base)
    for name in (
        "root2_livebench_if_astra_inference_adapter_v2.py",
        "root2_livebench_if_astra_inference_adapter_v3.py",
        "instruction_constraint_compiler_v1.py",
    ):
        src = ROOT / "canonical" / "runtime" / name
        dst = template / "canonical" / "runtime" / name
        shutil.copy2(src, dst)
    return template


def infer_one(template: pathlib.Path, q: dict, benchmark_id: str):
    with tempfile.TemporaryDirectory(prefix="lb-v11-case-") as td:
        root = pathlib.Path(td) / "root"
        shutil.copytree(template, root, dirs_exist_ok=True)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        req = {
            "benchmark_id": benchmark_id,
            "task_id": "REDACTED",
            "task_payload": {"instruction": q["turns"][0]},
            "allowed_tools": [],
        }
        try:
            cp = subprocess.run(
                [sys.executable, "-c", CASE_DRIVER],
                input=json.dumps(req),
                text=True,
                capture_output=True,
                cwd=root,
                env=env,
                timeout=45,
            )
            if cp.returncode != 0:
                return "", "PROCESS_EXIT_NONZERO", ""
            obj = json.loads(cp.stdout)
            status = str(obj.get("status") or "")
            route = str(obj.get("response_route") or "")
            answer = str(obj.get("answer") or "")
            if status == "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE" and answer:
                return answer, "PASS", route or "UNLABELED_PASS_ROUTE"
            if status == "BLOCKED__POLICY":
                return "", "POLICY_BLOCK", ""
            return "", "OTHER_BLOCK", ""
        except Exception:
            return "", "DRIVER_EXCEPTION", ""


def main(*, authorized: bool = False, activation_blob: str | None = None) -> int:
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V11_LAUNCHER_REQUIRED")
    if not isinstance(activation_blob, str) or re.fullmatch(r"[0-9a-f]{40}", activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V11_ACTIVATION_BLOB_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS") != "true" or str(os.environ.get("REPOSITORY_PRIVATE", "")).lower() != "false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("FAIL_CLOSED:PYTHON_3_12_REQUIRED")

    mod = load_base()
    with tempfile.TemporaryDirectory(prefix="livebench-v11-aggregate-") as td:
        base = pathlib.Path(td)

        # Zero-terminal-case preparation and scorer identity checks.
        mod.install_scorer_deps()
        mod.prepare_nltk(base)
        lb = mod.clone_livebench(base)
        sys.path.insert(0, str(lb / "livebench/if_runner"))
        from instruction_following_eval import evaluation_main as legacy_eval
        sys.path.insert(0, str(lb))
        from livebench.if_runner.ifbench import evaluation_lib as ifbench_eval

        template = build_template(base, mod)

        # Synthetic V3 route check, still before terminal dataset read.
        synth = {
            "turns": ["Use at least 5 unique words in the response."],
        }
        answer, cls, route = infer_one(template, synth, mod.BENCHMARK_ID)
        if cls != "PASS" or route != "LIVEBENCH_IF_SCORE_ONLY_STRUCTURAL_WITNESS_V3" or not answer:
            raise SystemExit("FAIL_CLOSED:V11_SYNTHETIC_V3_ROUTE")

        # Exact previously exposed prefix only. No case 73+ is ever selected.
        parquet = mod.download_dataset(base)
        questions = mod.parse_population(base, parquet)[:REPLAY_LIMIT]
        if len(questions) != REPLAY_LIMIT:
            raise RuntimeError("REPLAY_PREFIX_COUNT_MISMATCH")

        score_mass = 0.0
        follow_all_count = 0
        instruction_total = 0
        instruction_followed = 0
        scoring_error_count = 0
        class_hist = collections.Counter()
        route_hist = collections.Counter()

        for start in range(0, REPLAY_LIMIT, BATCH):
            current = questions[start:start+BATCH]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(BATCH, os.cpu_count() or 2)) as ex:
                raw = list(ex.map(lambda q: infer_one(template, q, mod.BENCHMARK_ID), current))
            for q, (answer, cls, route) in zip(current, raw):
                class_hist[cls] += 1
                if route:
                    route_hist[route] += 1
                if cls != "PASS":
                    instruction_total += len(q.get("instruction_id_list") or [])
                    continue
                score, all_ok, n, followed, score_err = mod.case_score(
                    legacy_eval, ifbench_eval, q, answer
                )
                score_mass += score
                follow_all_count += int(bool(all_ok))
                instruction_total += int(n)
                instruction_followed += int(followed)
                scoring_error_count += int(score_err is not None)

        out = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_V11_V3_REPLAY72_AGGREGATE_RESULT_V1",
            "status": "REPLAY72_AGGREGATE_COMPLETE",
            "benchmark_id": mod.BENCHMARK_ID,
            "activation_blob_sha": activation_blob,
            "replay_prefix_limit": REPLAY_LIMIT,
            "replayed_already_exposed_cases": REPLAY_LIMIT,
            "new_case_exposure": False,
            "case_73_or_later": False,
            "case_ids_emitted": False,
            "prompt_text_emitted": False,
            "response_text_emitted": False,
            "raw_exception_text_emitted": False,
            "aggregate_score_mass": score_mass,
            "aggregate_mean_percent": 100.0 * score_mass / REPLAY_LIMIT,
            "aggregate_follow_all_count": follow_all_count,
            "aggregate_instruction_total": instruction_total,
            "aggregate_instruction_followed": instruction_followed,
            "aggregate_instruction_follow_percent": (
                100.0 * instruction_followed / instruction_total if instruction_total else 0.0
            ),
            "scoring_error_count": scoring_error_count,
            "inference_class_histogram": dict(sorted(class_hist.items())),
            "response_route_histogram": dict(sorted(route_hist.items())),
            "dataset_revision": mod.DATASET_REV,
            "dataset_sha256": mod.DATASET_SHA256,
            "livebench_commit": mod.LIVEBENCH_COMMIT,
            "candidate_runtime": "V3_SCORE_ONLY_STRUCTURAL_WITNESS",
            "incremental_spend_usd": 0,
            "paid_external_model_or_api_used": False,
            "promotion_authority": False,
            "acceptance_credit_authority": False,
        }
        print("LIVEBENCH_V11_REPLAY72_AGGREGATE=" + json.dumps(out, sort_keys=True), flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_V11_LAUNCHER_REQUIRED")
