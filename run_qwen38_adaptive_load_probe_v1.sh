#!/usr/bin/env bash
set -euo pipefail

Q3_BYTES=13146393504
Q3_SHA="8c2a45ff85e7674ca185ec8eb6cdeab0e617ed9d8018caed0b64380eb2a67a5e"
Q3_FILE="Qwen3.8-27B-UD-Q3_K_XL.gguf"
Q2_BYTES=9828981664
Q2_SHA="fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"
Q2_FILE="Qwen3.8-27B-UD-Q2_K_XL.gguf"
HF_REV="313447f257f7ebde0b968e4778feef774546ed81"
LLAMA_COMMIT="0adcc3bb571011bff8b91335d0728a82845c421b"
RAM_HEADROOM=3000000000
DISK_HEADROOM=2500000000

python3 - <<'PY'
import json, os, shutil
mi={}
with open("/proc/meminfo") as f:
    for line in f:
        k,v=line.split(":",1)
        p=v.strip().split()
        if p and p[0].isdigit():
            n=int(p[0])*(1024 if len(p)>1 and p[1].lower()=="kb" else 1)
            mi[k]=n
cg=None
for path in ("/sys/fs/cgroup/memory.max","/sys/fs/cgroup/memory/memory.limit_in_bytes"):
    try:
        raw=open(path).read().strip()
        if raw != "max":
            v=int(raw)
            if 0 < v < 2**60:
                cg=v
                break
    except Exception:
        pass
disk=shutil.disk_usage(".")
effective=min([x for x in (mi.get("MemTotal",0),cg) if isinstance(x,int) and x>0], default=mi.get("MemTotal",0))
print(json.dumps({
 "phase":"PRELOAD_RESOURCE_MEASUREMENT",
 "disk_free_bytes":disk.free,
 "mem_total_bytes":mi.get("MemTotal"),
 "mem_available_bytes":mi.get("MemAvailable"),
 "cgroup_memory_limit_bytes":cg,
 "effective_memory_limit_bytes":effective,
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
for path in ("/sys/fs/cgroup/memory.max","/sys/fs/cgroup/memory/memory.limit_in_bytes"):
    try:
        raw=open(path).read().strip()
        if raw!="max":
            x=int(raw)
            if 0<x<2**60: cg=x; break
    except Exception: pass
vals=[x for x in (mi.get("MemTotal",0),cg) if x]
print(min(vals) if vals else 0)
PY
)"
DISK_FREE="$(df -B1 --output=avail . | tail -1 | tr -d ' ')"

if (( EFFECTIVE_MEM >= Q3_BYTES + RAM_HEADROOM && DISK_FREE >= Q3_BYTES + DISK_HEADROOM )); then
  SUBJECT="Q3_K_XL"; MODEL_BYTES="$Q3_BYTES"; MODEL_SHA="$Q3_SHA"; MODEL_FILE="$Q3_FILE"
elif (( EFFECTIVE_MEM >= Q2_BYTES + RAM_HEADROOM && DISK_FREE >= Q2_BYTES + DISK_HEADROOM )); then
  SUBJECT="Q2_K_XL"; MODEL_BYTES="$Q2_BYTES"; MODEL_SHA="$Q2_SHA"; MODEL_FILE="$Q2_FILE"
else
  echo '{"phase":"ADMISSION","status":"NO_STANDARD_RUNNER_SUBJECT_ADMITTED"}'
  exit 42
fi

echo "SELECTED_SUBJECT=$SUBJECT"
echo "MODEL_FILE=$MODEL_FILE"
echo "MODEL_BYTES=$MODEL_BYTES"

sudo rm -rf /usr/local/lib/android /usr/share/dotnet /opt/ghc || true
df -B1 .

git clone --depth 1 --branch b10502 https://github.com/ggml-org/llama.cpp.git llama.cpp
ACTUAL_LLAMA_COMMIT="$(git -C llama.cpp rev-parse HEAD)"
test "$ACTUAL_LLAMA_COMMIT" = "$LLAMA_COMMIT"

cmake -S llama.cpp -B llama.cpp/build   -DCMAKE_BUILD_TYPE=Release   -DGGML_NATIVE=OFF   -DLLAMA_CURL=OFF
cmake --build llama.cpp/build --config Release -j2 --target llama-cli

URL="https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/${HF_REV}/${MODEL_FILE}"
curl --fail --location --retry 5 --retry-all-errors   --output "$MODEL_FILE" "$URL"

ACTUAL_BYTES="$(stat -c %s "$MODEL_FILE")"
test "$ACTUAL_BYTES" = "$MODEL_BYTES"
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
 "schema":"PROJECT_BRAIN_QWEN38_ADAPTIVE_LOAD_PROBE_RESULT_V1",
 "selected_subject":"$SUBJECT",
 "model_bytes":int("$MODEL_BYTES"),
 "model_sha256":"$MODEL_SHA",
 "hf_revision":"$HF_REV",
 "llama_cpp_commit":"$LLAMA_COMMIT",
 "llama_exit_code":int("$RC"),
 "generation_nonempty":bool(out.strip()),
 "max_rss_bytes":None if not m else int(m.group(1))*1024,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0,
 "hard_nonclaims":[
   "LOAD_AND_SHORT_GENERATION_IS_NOT_SEMANTIC_QUALITY_PROOF",
   "LOAD_AND_SHORT_GENERATION_IS_NOT_LIVEBENCH_ACCEPTANCE",
   "QUANTIZED_SUBJECT_INHERITS_ZERO_SCORE_CREDIT"
 ]
},sort_keys=True))
PY

test "$RC" = "0"
test -s generation.txt
