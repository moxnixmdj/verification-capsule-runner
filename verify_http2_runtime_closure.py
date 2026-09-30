#!/usr/bin/env python3
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
M=ROOT/"http2_runtime_closure_manifest.json"
def blob(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
m=json.loads(M.read_text(encoding="utf-8"))
expected={x["path"]:x["git_blob_sha1"] for x in m["entries"]}
observed={}
for p in (ROOT/"canonical/runtime").rglob("*"):
    if p.is_file() and "__pycache__" not in p.parts:
        observed[p.relative_to(ROOT).as_posix()]=blob(p)
for rel in (
    "canonical/tasks/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json",
    "canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json",
):
    p=ROOT/rel
    if p.is_file(): observed[rel]=blob(p)
missing=sorted(set(expected)-set(observed))
extra=sorted(set(observed)-set(expected))
mismatch=sorted(k for k in expected.keys()&observed.keys() if expected[k]!=observed[k])
report={"schema":"PROJECT_BRAIN_HTTP2_RUNTIME_CLOSURE_PREFLIGHT_V1","status":"PASS" if not (missing or extra or mismatch) else "FAIL","canonical_brain_commit":m["canonical_brain_commit"],"entry_count":len(expected),"missing":missing,"extra":extra,"mismatch":mismatch}
(ROOT/"http2-runtime-closure-preflight.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["status"]=="PASS" else 1)
