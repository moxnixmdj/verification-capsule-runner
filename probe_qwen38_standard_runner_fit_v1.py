#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import platform
import shutil

Q3_BYTES = 13_146_393_504
Q3_SHA256 = "8c2a45ff85e7674ca185ec8eb6cdeab0e617ed9d8018caed0b64380eb2a67a5e"
Q2_BYTES = 9_828_981_664
Q2_SHA256 = "fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"

# Precommitted conservative load-probe gate. This does NOT assert inference fit.
DISK_HEADROOM = 2_500_000_000
RAM_HEADROOM = 3_000_000_000


def read_text(path: str):
    try:
        return pathlib.Path(path).read_text().strip()
    except Exception:
        return None


def meminfo():
    out={}
    raw=read_text("/proc/meminfo") or ""
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k,v=line.split(":",1)
        parts=v.strip().split()
        if parts and parts[0].isdigit():
            n=int(parts[0])
            if len(parts)>1 and parts[1].lower()=="kb":
                n*=1024
            out[k]=n
    return out


def cgroup_limit():
    for path in ("/sys/fs/cgroup/memory.max","/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        raw=read_text(path)
        if raw and raw!="max":
            try:
                value=int(raw)
                if value>0 and value < 2**60:
                    return value
            except Exception:
                pass
    return None


def tree_size(path: str):
    p=pathlib.Path(path)
    if not p.exists():
        return None
    total=0
    try:
        for root, dirs, files in os.walk(p):
            for name in files:
                try:
                    total += (pathlib.Path(root)/name).stat().st_size
                except Exception:
                    pass
        return total
    except Exception:
        return None


def main():
    disk=shutil.disk_usage(".")
    mi=meminfo()
    cg=cgroup_limit()
    mem_total=mi.get("MemTotal",0)
    mem_available=mi.get("MemAvailable",0)
    effective_total=min([x for x in (mem_total,cg) if isinstance(x,int) and x>0], default=mem_total)
    # We use total for a pre-download admission gate because a fresh dedicated
    # load job will start after this probe. Actual model load remains mandatory.
    q3_disk_ok=disk.free >= Q3_BYTES + DISK_HEADROOM
    q2_disk_ok=disk.free >= Q2_BYTES + DISK_HEADROOM
    q3_ram_nominal=effective_total >= Q3_BYTES + RAM_HEADROOM
    q2_ram_nominal=effective_total >= Q2_BYTES + RAM_HEADROOM

    if q3_disk_ok and q3_ram_nominal:
        next_subject="Q3_K_XL"
    elif q2_disk_ok and q2_ram_nominal:
        next_subject="Q2_K_XL"
    else:
        next_subject="NO_STANDARD_RUNNER_LOAD_PROBE_ADMITTED"

    out={
        "schema":"PROJECT_BRAIN_QWEN38_STANDARD_RUNNER_RESOURCE_PROBE_V1",
        "conclusion":"MEASUREMENT_ONLY",
        "runner":{
            "platform":platform.platform(),
            "machine":platform.machine(),
            "cpu_count":os.cpu_count(),
            "disk_total_bytes":disk.total,
            "disk_used_bytes":disk.used,
            "disk_free_bytes":disk.free,
            "mem_total_bytes":mem_total,
            "mem_available_bytes_at_probe":mem_available,
            "cgroup_memory_limit_bytes":cg,
            "effective_memory_limit_bytes":effective_total,
            "swap_total_bytes":mi.get("SwapTotal",0),
        },
        "subjects":{
            "Q3_K_XL":{"bytes":Q3_BYTES,"sha256":Q3_SHA256},
            "Q2_K_XL":{"bytes":Q2_BYTES,"sha256":Q2_SHA256},
        },
        "precommitted_headroom":{
            "disk_bytes":DISK_HEADROOM,
            "ram_bytes":RAM_HEADROOM,
        },
        "admission":{
            "q3_disk_ok":q3_disk_ok,
            "q3_ram_nominal":q3_ram_nominal,
            "q3_load_probe_eligible":q3_disk_ok and q3_ram_nominal,
            "q2_disk_ok":q2_disk_ok,
            "q2_ram_nominal":q2_ram_nominal,
            "q2_load_probe_eligible":q2_disk_ok and q2_ram_nominal,
            "next_subject_for_real_load_probe":next_subject,
        },
        "large_preinstalled_paths_bytes":{
            "/opt/hostedtoolcache":tree_size("/opt/hostedtoolcache"),
            "/usr/local/lib/android":tree_size("/usr/local/lib/android"),
            "/usr/share/dotnet":tree_size("/usr/share/dotnet"),
        },
        "hard_nonclaims":[
            "RESOURCE_ADMISSION_IS_NOT_MODEL_LOAD_PROOF",
            "RESOURCE_ADMISSION_IS_NOT_INFERENCE_PROOF",
            "RESOURCE_ADMISSION_IS_NOT_LIVEBENCH_OR_SEMANTIC_CAPABILITY_CREDIT",
            "NO_MODEL_BYTES_DOWNLOADED_BY_THIS_PROBE"
        ],
        "network_model_downloads":0,
        "terminal_cases_consumed":0,
        "incremental_spend_usd":0,
    }
    print(json.dumps(out,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
