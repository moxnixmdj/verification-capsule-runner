#!/usr/bin/env bash
set -euo pipefail

MODEL_FILE="Qwen3.8-27B-UD-Q2_K_XL.gguf"
MODEL_BYTES=9828981664
MODEL_SHA="fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"
HF_REV="27af057ecb382ddfea5d12837360a8980560e3ed"
LLAMA_COMMIT="0d9ceae1e38291035605613ab41a8f5e693d6fcd"
DISK_HEADROOM=2500000000
RAM_HEADROOM=3000000000

python3 - <<'PY'
import json, os, shutil
mi={}
with open("/proc/meminfo") as f:
    for line in f:
        k,v=line.split(":",1)
        p=v.strip().split()
        if p and p[0].isdigit():
            mi[k]=int(p[0])*(1024 if len(p)>1 and p[1].lower()=="kb" else 1)
cg=None
for p in ("/sys/fs/cgroup/memory.max","/sys/fs/cgroup/memory/memory.limit_in_bytes"):
    try:
        raw=open(p).read().strip()
        if raw!="max":
            x=int(raw)
            if 0<x<2**60:
                cg=x
                break
    except Exception:
        pass
d=shutil.disk_usage(".")
vals=[x for x in (mi.get("MemTotal",0),cg) if isinstance(x,int) and x>0]
effective=min(vals) if vals else mi.get("MemTotal",0)
print(json.dumps({
 "schema":"PROJECT_BRAIN_QWEN38_Q2_PRELOAD_RESOURCE_MEASUREMENT_V1",
 "disk_free_bytes":d.free,
 "disk_total_bytes":d.total,
 "mem_total_bytes":mi.get("MemTotal"),
 "mem_available_bytes":mi.get("MemAvailable"),
 "cgroup_memory_limit_bytes":cg,
 "effective_memory_limit_bytes":effective,
 "swap_total_bytes":mi.get("SwapTotal",0),
 "cpu_count":os.cpu_count()
},sort_keys=True))
PY

EFFECTIVE_MEM="$(python3 - <<'PY'
mi={}
with open("/proc/meminfo") as f:
    for line in f:
        k,v=line.split(":",1)
        p=v.strip().split()
        if p and p[0].isdigit():
            mi[k]=int(p[0])*(1024 if len(p)>1 and p[1].lower()=="kb" else 1)
cg=None
for p in ("/sys/fs/cgroup/memory.max","/sys/fs/cgroup/memory/memory.limit_in_bytes"):
    try:
        raw=open(p).read().strip()
        if raw!="max":
            x=int(raw)
            if 0<x<2**60:
                cg=x; break
    except Exception: pass
vals=[x for x in (mi.get("MemTotal",0),cg) if x]
print(min(vals) if vals else 0)
PY
)"
DISK_FREE="$(df -B1 --output=avail . | tail -1 | tr -d ' ')"

if (( EFFECTIVE_MEM < MODEL_BYTES + RAM_HEADROOM )); then
  echo "Q2_PRELOAD_GATE=FAIL_RAM"
  exit 42
fi
if (( DISK_FREE < MODEL_BYTES + DISK_HEADROOM )); then
  echo "Q2_PRELOAD_GATE=FAIL_DISK"
  exit 43
fi
echo "Q2_PRELOAD_GATE=PASS"

# Disposable runner only. Delete irrelevant preinstalled SDKs to maximize
# model/build headroom; this does not touch any user device or repository state.
sudo rm -rf /usr/local/lib/android /usr/share/dotnet /opt/ghc || true
df -B1 .

git init llama.cpp
git -C llama.cpp remote add origin https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp fetch --depth 1 origin "$LLAMA_COMMIT"
git -C llama.cpp checkout --detach FETCH_HEAD
test "$(git -C llama.cpp rev-parse HEAD)" = "$LLAMA_COMMIT"

cmake -S llama.cpp -B llama.cpp/build   -DCMAKE_BUILD_TYPE=Release   -DGGML_NATIVE=OFF   -DLLAMA_CURL=OFF
cmake --build llama.cpp/build --config Release -j2 --target llama-cli

URL="https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/${HF_REV}/${MODEL_FILE}"
curl --fail --location --retry 5 --retry-all-errors   --output "$MODEL_FILE" "$URL"

test "$(stat -c %s "$MODEL_FILE")" = "$MODEL_BYTES"
echo "$MODEL_SHA  $MODEL_FILE" | sha256sum -c -

set +e
/usr/bin/time -v llama.cpp/build/bin/llama-cli   -m "$MODEL_FILE"   -ngl 0   -c 256   -n 8   --temp 0   -p "Answer with only the numeral: 2+2="   > generation.txt 2> timing_and_stderr.txt
RC=$?
set -e

echo "LLAMA_EXIT_CODE=$RC"
echo "GENERATION_BEGIN"
cat generation.txt
echo "GENERATION_END"
echo "RESOURCE_TIMING_BEGIN"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)|User time|System time|Percent of CPU' timing_and_stderr.txt || true
echo "RESOURCE_TIMING_END"

python3 - <<PY
import json, pathlib, re
stderr=pathlib.Path("timing_and_stderr.txt").read_text(errors="replace")
out=pathlib.Path("generation.txt").read_text(errors="replace")
m=re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)",stderr)
print(json.dumps({
 "schema":"PROJECT_BRAIN_QWEN38_Q2_EXACT_LOAD_PROBE_RESULT_V1",
 "status":"PASS" if int("$RC")==0 and bool(out.strip()) else "FAIL",
 "exact_model_bytes":int("$MODEL_BYTES"),
 "exact_model_sha256":"$MODEL_SHA",
 "source_revision":"$HF_REV",
 "llama_cpp_commit":"$LLAMA_COMMIT",
 "llama_exit_code":int("$RC"),
 "generation_nonempty":bool(out.strip()),
 "max_rss_bytes":None if not m else int(m.group(1))*1024,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0,
 "hard_nonclaims":[
   "LOAD_AND_SHORT_GENERATION_IS_NOT_FOUR_TASK_SEMANTIC_QUALIFICATION",
   "LOAD_AND_SHORT_GENERATION_IS_NOT_LIVEBENCH_ACCEPTANCE",
   "QUANTIZED_SUBJECT_INHERITS_ZERO_BF16_SCORE_CREDIT"
 ]
},sort_keys=True))
PY

test "$RC" = "0"
test -s generation.txt
