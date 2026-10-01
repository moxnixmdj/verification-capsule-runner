#!/usr/bin/env python3
import hashlib, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
task_path=ROOT/"canonical/tasks/PARENT_ASTRONOMY_EROS_KEPLER_REAL_TASK_20260930_001.json"
raw_task=task_path.read_bytes()
task=json.loads(raw_task)
url=task["source"]["url"]

def get_path(obj,path):
    cur=obj
    for part in path:
        cur=cur[int(part)] if isinstance(cur,list) else cur[str(part)]
    return cur

req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-JPL-Preflight-V2/1"})
with urllib.request.urlopen(req,timeout=20) as resp:
    raw=resp.read(1000000)
    status=int(resp.status)
payload=json.loads(raw.decode("utf-8"))
fail=[]
sig=payload.get("signature") or {}
if "JPL" not in str(sig.get("source") or ""): fail.append("SIGNATURE_SOURCE_NOT_JPL")
obj=payload.get("object") or {}
if "Eros" not in str(obj.get("shortname") or obj.get("fullname") or ""): fail.append("OBJECT_NOT_EROS")
try:
    a_item=payload["orbit"]["elements"][task["source"]["semimajor_axis_json_path"][2]]
    a_raw=get_path(payload,task["source"]["semimajor_axis_json_path"])
except Exception as exc:
    a_item=None; a_raw=None; fail.append("CONFIGURED_A_PATH_FAILED:"+type(exc).__name__)
try:
    p_item=payload["orbit"]["elements"][task["source"]["observed_period_json_path"][2]]
    p_raw=get_path(payload,task["source"]["observed_period_json_path"])
except Exception as exc:
    p_item=None; p_raw=None; fail.append("CONFIGURED_PERIOD_PATH_FAILED:"+type(exc).__name__)
if not isinstance(a_item,dict) or a_item.get("name")!="a": fail.append("CONFIGURED_A_PATH_NOT_SEMIMAJOR_AXIS")
if not isinstance(p_item,dict) or p_item.get("name")!="per": fail.append("CONFIGURED_PERIOD_PATH_NOT_PERIOD")
try: a=float(a_raw)
except Exception: fail.append("CONFIGURED_A_VALUE_NONNUMERIC"); a=None
try: period=float(p_raw)
except Exception: fail.append("CONFIGURED_PERIOD_VALUE_NONNUMERIC"); period=None
if isinstance(a_item,dict) and a_item.get("units")!="au": fail.append("A_UNITS_MISMATCH")
if isinstance(p_item,dict) and p_item.get("units")!="d": fail.append("PERIOD_UNITS_MISMATCH")
report={
  "schema":"PROJECT_BRAIN_PARENT_ASTRONOMY_JPL_SOURCE_PREFLIGHT_V2",
  "task_id":task["task_id"],
  "task_blob_sha1":"4cb0fbb4f46cf3c7302688197117cbaffe2d3943",
  "task_sha256":hashlib.sha256(raw_task).hexdigest(),
  "status":"PASS" if not fail else "FAIL",
  "http_status":status,
  "signature":sig,
  "object":obj.get("shortname") or obj.get("fullname"),
  "configured_semimajor_axis_path":task["source"]["semimajor_axis_json_path"],
  "configured_period_path":task["source"]["observed_period_json_path"],
  "semimajor_axis_au":a,
  "jpl_period_days":period,
  "a_item":a_item,
  "period_item":p_item,
  "failures":fail,
}
(ROOT/"parent-astronomy-jpl-preflight-v2.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
if fail: raise SystemExit(1)
