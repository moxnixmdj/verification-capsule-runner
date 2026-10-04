#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, shutil

MODEL_BYTES = 9_828_981_664
DISK_RESERVE_BYTES = 2_000_000_000
MEMORY_RESERVE_BYTES = 2_000_000_000

def read_int(path):
    try:
        raw=pathlib.Path(path).read_text().strip()
        if raw == "max":
            return None
        return int(raw)
    except Exception:
        return None

def meminfo():
    out={}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue
        k,v=line.split(":",1)
        parts=v.strip().split()
        if not parts:
            continue
        n=int(parts[0])
        if len(parts)>1 and parts[1].lower()=="kb":
            n*=1024
        out[k]=n
    return out

if os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("FAIL_CLOSED:GITHUB_ACTIONS_REQUIRED")

du=shutil.disk_usage("/")
mi=meminfo()
cgroup_max=read_int("/sys/fs/cgroup/memory.max")
cgroup_current=read_int("/sys/fs/cgroup/memory.current")
host_total=mi.get("MemTotal",0)
host_available=mi.get("MemAvailable",0)

effective_limit = host_total
if cgroup_max is not None and cgroup_max > 0:
    effective_limit=min(effective_limit,cgroup_max)

effective_available = host_available
if cgroup_max is not None and cgroup_current is not None:
    effective_available=min(effective_available,max(0,cgroup_max-cgroup_current))

disk_required=MODEL_BYTES+DISK_RESERVE_BYTES
mem_required=MODEL_BYTES+MEMORY_RESERVE_BYTES

result={
  "schema":"PROJECT_BRAIN_QWEN38_Q2_STANDARD_RUNNER_RESOURCE_PREFLIGHT_V1",
  "runner_os":os.environ.get("RUNNER_OS"),
  "runner_arch":os.environ.get("RUNNER_ARCH"),
  "model_subject":{
    "repository":"unsloth/Qwen3.8-27B-GGUF",
    "file":"Qwen3.8-27B-UD-Q2_K_XL.gguf",
    "bytes":MODEL_BYTES,
    "sha256":"fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0",
  },
  "observed":{
    "disk_total_bytes":du.total,
    "disk_free_bytes":du.free,
    "host_mem_total_bytes":host_total,
    "host_mem_available_bytes":host_available,
    "cgroup_memory_max_bytes":cgroup_max,
    "cgroup_memory_current_bytes":cgroup_current,
    "effective_memory_limit_bytes":effective_limit,
    "effective_memory_available_bytes":effective_available,
  },
  "preflight":{
    "disk_reserve_bytes":DISK_RESERVE_BYTES,
    "memory_reserve_bytes":MEMORY_RESERVE_BYTES,
    "disk_required_bytes":disk_required,
    "memory_required_bytes":mem_required,
    "disk_streaming_fit":du.free >= disk_required,
    "memory_nominal_fit":effective_available >= mem_required,
  },
  "firewall":{
    "model_downloaded":False,
    "terminal_cases_read":0,
    "terminal_content_read":False,
    "network_model_inference":False,
    "incremental_spend_usd":0,
  },
}
result["status"] = (
    "PASS_NOMINAL_RESOURCE_FIT__EXECUTION_STILL_UNPROVED"
    if result["preflight"]["disk_streaming_fit"] and result["preflight"]["memory_nominal_fit"]
    else "FAIL_NOMINAL_RESOURCE_FIT"
)
print("QWEN38_Q2_RESOURCE_PREFLIGHT="+json.dumps(result,sort_keys=True))
if result["status"] == "FAIL_NOMINAL_RESOURCE_FIT":
    raise SystemExit(2)
