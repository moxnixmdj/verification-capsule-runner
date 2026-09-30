#!/usr/bin/env python3
import hashlib, json, pathlib, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
TASK=ROOT/"canonical/tasks/PARENT_METEOROLOGY_NASA_POWER_DAILY_MEAN_REAL_TASK_20260930_001.json"
TASK_BLOB="8fbe0b739a796733d20368cc629247379d133765"

def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest()

if git_blob(TASK)!=TASK_BLOB:
    raise SystemExit("TASK_BLOB_MISMATCH:"+git_blob(TASK))
task=json.loads(TASK.read_text(encoding="utf-8"))

checks=[]
failures=[]
for source in task["sources"]:
    req=urllib.request.Request(source["url"],headers={"User-Agent":"ProjectBrain-NASA-POWER-Source-Preflight/1"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        raw=resp.read(3000000)
        status=resp.status
        content_type=resp.headers.get("content-type","")
    try:
        payload=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        failures.append(source["id"]+":JSON_PARSE:"+type(exc).__name__)
        continue
    cur=payload
    try:
        for key in source["json_path"]:
            cur=cur[key]
    except Exception as exc:
        failures.append(source["id"]+":PATH_MISSING:"+type(exc).__name__)
        continue
    numeric=isinstance(cur,(int,float)) and not isinstance(cur,bool)
    if not numeric:
        failures.append(source["id"]+":VALUE_NOT_NUMERIC")
    checks.append({
      "source_id":source["id"],
      "http_status":status,
      "content_type":content_type,
      "body_sha256":hashlib.sha256(raw).hexdigest(),
      "json_path":source["json_path"],
      "numeric_value_present":numeric,
      "declared_units":source["units"],
      "answer_value_redacted":True
    })

report={
  "schema":"PROJECT_BRAIN_PARENT_METEOROLOGY_NASA_POWER_SOURCE_PREFLIGHT_V1",
  "task_id":task["task_id"],
  "task_blob":TASK_BLOB,
  "status":"PASS" if not failures and len(checks)==3 else "FAIL",
  "answer_computed":False,
  "scientific_relation_evaluated":False,
  "source_checks":checks,
  "failures":failures
}
path=ROOT/"PARENT_METEOROLOGY_NASA_POWER_PREFLIGHT.json"
path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if report["status"]!="PASS":
    raise SystemExit(1)
