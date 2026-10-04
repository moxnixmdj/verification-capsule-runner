#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, subprocess, sys, tempfile
import execute_livebench_if_threshold_v2 as e

def main() -> int:
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert str(os.environ.get("REPOSITORY_PRIVATE","")).lower() == "false"
    with tempfile.TemporaryDirectory(prefix="lb-template-diagnostic-") as td:
        base = pathlib.Path(td)
        template = e.build_runtime_template(base)
        root = template
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        req = {
            "benchmark_id": e.BENCHMARK_ID,
            "task_id": "SYNTHETIC_POSTRUN_TEMPLATE_DIAGNOSTIC",
            "task_payload": {"instruction": "Respond with exactly SYNTHETIC_OK."},
            "allowed_tools": [],
        }
        cp = subprocess.run(
            [sys.executable, "-c", e.CASE_DRIVER],
            input=json.dumps(req),
            text=True,
            capture_output=True,
            cwd=root,
            env=env,
            timeout=45,
        )
        print("RETURN_CODE="+str(cp.returncode))
        print("STDOUT_BEGIN")
        print(cp.stdout)
        print("STDOUT_END")
        print("STDERR_BEGIN")
        print(cp.stderr)
        print("STDERR_END")
        print("TERMINAL_CASE_CONTENT_READ=false")
        print("TERMINAL_CASES_CONSUMED=0")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
