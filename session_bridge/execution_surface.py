#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any


def classify_python_package_policy(profile: dict[str, Any]) -> str:
    py = profile.get("python") or {}
    if not py.get("present"):
        return "PYTHON_UNAVAILABLE"
    managed = bool(py.get("externally_managed"))
    pip_ok = bool(py.get("pip_available"))
    venv_ok = bool(py.get("venv_usable"))
    if managed and venv_ok:
        return "VENV_REQUIRED"
    if managed and not venv_ok:
        return "NO_SAFE_PYTHON_INSTALL_ROUTE"
    if pip_ok:
        return "SYSTEM_PIP_ALLOWED_OR_UNMANAGED"
    if venv_ok:
        return "VENV_ONLY"
    return "NO_PYTHON_PACKAGE_INSTALL_ROUTE"


def _docker_exec(container: str, script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "exec", container, "/bin/sh", "-lc", script],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


def probe_running_container(container: str = "brain-bridge-task") -> dict[str, Any]:
    os_cp = _docker_exec(container, "cat /etc/os-release 2>/dev/null || true")
    py_cp = _docker_exec(container, "command -v python3 || true")
    py_path = (py_cp.stdout or "").strip()
    profile: dict[str, Any] = {
        "schema": "BRAIN_EXECUTION_SURFACE_PROFILE_V1",
        "status": "PASS",
        "container": container,
        "os_release": (os_cp.stdout or "")[-12000:],
        "python": {"present": bool(py_path)},
    }
    if not py_path:
        profile["python_package_policy"] = classify_python_package_policy(profile)
        return profile

    script = r"""python3 - <<'PY'
import json, os, pathlib, subprocess, sys, sysconfig, tempfile, shutil
paths=sysconfig.get_paths()
candidates=[]
for key in ("stdlib","platstdlib"):
    p=paths.get(key)
    if p:
        candidates.append(str(pathlib.Path(p)/"EXTERNALLY-MANAGED"))
candidates.append(f"/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}/EXTERNALLY-MANAGED")
markers=sorted({p for p in candidates if os.path.exists(p)})
pip_cp=subprocess.run([sys.executable,"-m","pip","--version"],text=True,capture_output=True)
tmp=tempfile.mkdtemp(prefix="brain-surface-venv-")
venv_cp=subprocess.run([sys.executable,"-m","venv",tmp],text=True,capture_output=True)
venv_pip_ok=False
if venv_cp.returncode==0:
    vp=pathlib.Path(tmp)/"bin"/"python"
    q=subprocess.run([str(vp),"-m","pip","--version"],text=True,capture_output=True)
    venv_pip_ok=(q.returncode==0)
shutil.rmtree(tmp,ignore_errors=True)
print(json.dumps({
  "present": True,
  "executable": sys.executable,
  "version": sys.version,
  "prefix": sys.prefix,
  "base_prefix": sys.base_prefix,
  "externally_managed": bool(markers),
  "externally_managed_markers": markers,
  "pip_available": pip_cp.returncode==0,
  "pip_version": (pip_cp.stdout or pip_cp.stderr).strip(),
  "venv_usable": venv_cp.returncode==0 and venv_pip_ok,
  "venv_probe_exit_code": venv_cp.returncode,
  "venv_probe_stderr": (venv_cp.stderr or "")[-2000:]
}, sort_keys=True))
PY"""
    cp = _docker_exec(container, script)
    if cp.returncode != 0:
        profile["status"] = "FAIL"
        profile["probe_error"] = (cp.stderr or cp.stdout or "")[-4000:]
        profile["python_package_policy"] = "UNKNOWN_FAIL_CLOSED"
        return profile
    try:
        py = json.loads((cp.stdout or "").strip())
    except Exception as exc:
        profile["status"] = "FAIL"
        profile["probe_error"] = f"INVALID_PYTHON_PROBE_JSON:{exc}:{(cp.stdout or '')[-2000:]}"
        profile["python_package_policy"] = "UNKNOWN_FAIL_CLOSED"
        return profile
    profile["python"] = py
    profile["python_package_policy"] = classify_python_package_policy(profile)
    profile["safe_python_install_guidance"] = {
        "VENV_REQUIRED": "CREATE_TASK_LOCAL_VENV_AND_USE_ITS_PYTHON_PIP__DO_NOT_SYSTEM_PIP",
        "NO_SAFE_PYTHON_INSTALL_ROUTE": "FAIL_STAGE_B_IF_NON_SYSTEM_PYTHON_PACKAGES_ARE_REQUIRED",
        "SYSTEM_PIP_ALLOWED_OR_UNMANAGED": "SYSTEM_OR_VENV_PIP_MAY_BE_USED__VENV_PREFERRED_FOR_ISOLATION",
        "VENV_ONLY": "CREATE_TASK_LOCAL_VENV_AND_USE_ITS_PYTHON_PIP",
        "PYTHON_UNAVAILABLE": "DO_NOT_ASSUME_PYTHON_ROUTE_EXISTS",
        "NO_PYTHON_PACKAGE_INSTALL_ROUTE": "FAIL_STAGE_B_IF_PYTHON_PACKAGES_ARE_REQUIRED",
        "UNKNOWN_FAIL_CLOSED": "FAIL_STAGE_B",
    }[profile["python_package_policy"]]
    return profile


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--container",default="brain-bridge-task")
    args=ap.parse_args()
    profile=probe_running_container(args.container)
    print(json.dumps(profile,indent=2,sort_keys=True))
    return 0 if profile.get("status")=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
