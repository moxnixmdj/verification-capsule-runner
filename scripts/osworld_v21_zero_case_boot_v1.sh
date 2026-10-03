#!/usr/bin/env bash
set -uo pipefail
OUT=results/osworld_v21_zero_case_boot_v1.json
mkdir -p results /tmp/osw/vm
ART=https://huggingface.co/datasets/xlangai/v2-image/resolve/6e16459a2feb5a8f1ed65babcfe7a2a6205d049d/osworld-v2-ubuntu-x86.qcow2.zip
SHA=14b08aa7ba6c023ecb91d46de8df5de32af4d1d6bd75ea925519caf9677fc8b3
SIZE=14891811084
IMG=happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9
KVM=false; test -e /dev/kvm && KVM=true
DL=false; HASH=false; UNZIP=false; PULL=false; BOOT=false; HTTP=0; ERR=""
if [ "$KVM" != true ]; then ERR=KVM_ABSENT; fi
if [ -z "$ERR" ]; then curl -L --fail --retry 4 -o /tmp/osw/vm.zip "$ART" && DL=true || ERR=DOWNLOAD_FAILED; fi
if [ -z "$ERR" ]; then
  A="$(stat -c %s /tmp/osw/vm.zip)"; H="$(sha256sum /tmp/osw/vm.zip|cut -d' ' -f1)"
  [ "$A" = "$SIZE" ] && [ "$H" = "$SHA" ] && HASH=true || ERR=IDENTITY_MISMATCH
fi
if [ -z "$ERR" ]; then unzip -q /tmp/osw/vm.zip -d /tmp/osw/vm && test -s /tmp/osw/vm/osworld-v2-ubuntu-x86.qcow2 && UNZIP=true || ERR=UNZIP_FAILED; fi
if [ -z "$ERR" ]; then docker pull "$IMG" && PULL=true || ERR=IMAGE_PULL_FAILED; fi
cleanup(){ docker rm -f osw-v21 >/dev/null 2>&1 || true; }; trap cleanup EXIT
if [ -z "$ERR" ]; then
  docker run -d --name osw-v21 --cap-add NET_ADMIN --device /dev/kvm -e DISK_SIZE=32G -e RAM_SIZE=4G -e CPU_CORES=4 -v /tmp/osw/vm/osworld-v2-ubuntu-x86.qcow2:/System.qcow2:ro -p 5000:5000 -p 8006:8006 -p 9222:9222 -p 8080:8080 "$IMG" >/dev/null || ERR=CONTAINER_START_FAILED
fi
if [ -z "$ERR" ]; then
  for i in $(seq 1 150); do
    HTTP="$(curl -s -o /tmp/shot.png -w '%{http_code}' --max-time 5 http://127.0.0.1:5000/screenshot || true)"
    if [ "$HTTP" = 200 ] && test -s /tmp/shot.png; then BOOT=true; break; fi
    docker inspect -f '{{.State.Running}}' osw-v21 2>/dev/null | grep -q true || { ERR=CONTAINER_EXITED; break; }
    sleep 2
  done
  [ "$BOOT" = true ] || [ -n "$ERR" ] || ERR=NOT_READY
fi
export KVM DL HASH UNZIP PULL BOOT HTTP ERR SIZE SHA IMG
python - <<'PY'
import json,os,subprocess
b=lambda k: os.environ.get(k)=="true"
out={"schema":"PROJECT_BRAIN_OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_RESULT_V1","date":"2026-10-03",
"status":"PASS__PINNED_OSWORLD_V21_DOCKER_VM_BOOT_AND_SCREENSHOT_READY__ZERO_TERMINAL_CASES" if b("BOOT") else "FAIL_CLOSED__ZERO_CASE_BOOT_PREFLIGHT",
"runner":{"image":"ubuntu-24.04","cpu_count":int(subprocess.check_output(["nproc"],text=True)),"kvm_present":b("KVM")},
"binding":{"release":"osworld-v2.1","artifact_size_bytes":int(os.environ["SIZE"]),"artifact_sha256":os.environ["SHA"],"runtime_image":os.environ["IMG"]},
"checks":{"download":b("DL"),"identity":b("HASH"),"unzip":b("UNZIP"),"image_pull":b("PULL"),"vm_screenshot_ready":b("BOOT"),"screenshot_http_status":int(os.environ.get("HTTP") or 0)},
"error_class":os.environ.get("ERR") or None,"terminal_cases_consumed":0,"task_files_read":0,"task_assets_read":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
open("results/osworld_v21_zero_case_boot_v1.json","w").write(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps(out,indent=2,sort_keys=True))
PY
[ "$BOOT" = true ]
