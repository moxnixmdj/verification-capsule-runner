#!/usr/bin/env python3
import json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
task=json.loads((ROOT/"canonical/tasks/PARENT_ASTRONOMY_EROS_KEPLER_REAL_TASK_20260930_001.json").read_text())
url=task["source"]["url"]
req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-JPL-Preflight/1"})
with urllib.request.urlopen(req,timeout=20) as resp:
    raw=resp.read(1000000)
    status=int(resp.status)
payload=json.loads(raw.decode("utf-8"))
fail=[]
sig=payload.get("signature") or {}
if "JPL" not in str(sig.get("source") or ""): fail.append("SIGNATURE_SOURCE_NOT_JPL")
obj=payload.get("object") or {}
if "Eros" not in str(obj.get("shortname") or obj.get("fullname") or ""): fail.append("OBJECT_NOT_EROS")
elements=((payload.get("orbit") or {}).get("elements") or [])
by_name={str(x.get("name")):x for x in elements if isinstance(x,dict)}
for name,units in (("a","au"),("per","d")):
    item=by_name.get(name)
    if not isinstance(item,dict): fail.append("ELEMENT_MISSING:"+name); continue
    try: float(item.get("value"))
    except Exception: fail.append("ELEMENT_NONNUMERIC:"+name)
    if str(item.get("units") or "")!=units: fail.append("ELEMENT_UNITS_MISMATCH:"+name)
report={
  "schema":"PROJECT_BRAIN_PARENT_ASTRONOMY_JPL_SOURCE_PREFLIGHT_V1",
  "task_id":task["task_id"],
  "status":"PASS" if not fail else "FAIL",
  "http_status":status,
  "signature":sig,
  "object":obj.get("shortname") or obj.get("fullname"),
  "a":by_name.get("a"),
  "per":by_name.get("per"),
  "failures":fail,
}
(ROOT/"parent-astronomy-jpl-preflight.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
if fail: raise SystemExit(1)
