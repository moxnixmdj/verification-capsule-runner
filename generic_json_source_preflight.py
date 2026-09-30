#!/usr/bin/env python3
import hashlib, json, math, pathlib, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
MANIFEST=ROOT/"generic-json-source-preflight-manifest.json"
REPORT=ROOT/"generic-json-source-preflight-report.json"

def resolve(payload,path):
    cur=payload
    for part in path:
        cur=cur[part]
    return cur

manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
if manifest.get("schema")!="PROJECT_BRAIN_GENERIC_JSON_SOURCE_PREFLIGHT_MANIFEST_V1":
    raise SystemExit("MANIFEST_SCHEMA_INVALID")
sources=manifest.get("sources")
if not isinstance(sources,list) or not sources:
    raise SystemExit("SOURCES_REQUIRED")

records=[]
failures=[]
for src in sources:
    name=str(src.get("name") or "")
    url=str(src.get("url") or "")
    path=src.get("json_path")
    expected=str(src.get("expected_type") or "")
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Generic-JSON-Preflight/1"})
        with urllib.request.urlopen(req,timeout=25) as resp:
            status=int(resp.status)
            raw=resp.read(1_000_000)
        payload=json.loads(raw.decode("utf-8"))
        value=resolve(payload,path)
        if isinstance(value,bool):
            observed="boolean"
        elif isinstance(value,(int,float)) and math.isfinite(float(value)):
            observed="number"
        elif isinstance(value,str):
            observed="string"
        elif isinstance(value,list):
            observed="array"
        elif isinstance(value,dict):
            observed="object"
        elif value is None:
            observed="null"
        else:
            observed=type(value).__name__
        if status!=200:
            failures.append(name+":HTTP_"+str(status))
        if observed!=expected:
            failures.append(name+":TYPE_"+observed+"_EXPECTED_"+expected)
        records.append({
          "name":name,
          "url":url,
          "http_status":status,
          "json_path":path,
          "observed_type":observed,
          "response_sha256":hashlib.sha256(raw).hexdigest()
        })
    except Exception as exc:
        failures.append(name+":"+type(exc).__name__+":"+str(exc))

report={
  "schema":"PROJECT_BRAIN_GENERIC_JSON_SOURCE_PREFLIGHT_REPORT_V1",
  "task_id":manifest.get("task_id"),
  "status":"PASS" if not failures else "FAIL",
  "source_only_preflight":True,
  "task_executed":False,
  "values_recorded":False,
  "records":records,
  "failures":failures,
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if failures:
    raise SystemExit(1)
