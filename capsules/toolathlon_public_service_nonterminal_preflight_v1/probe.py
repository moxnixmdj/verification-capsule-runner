from __future__ import annotations
import json, urllib.request, urllib.error

URL="http://47.253.6.47:8080/check_server_status"
req=urllib.request.Request(URL,headers={"User-Agent":"Project-Brain-Toolathlon-Nonterminal-Preflight/1.0"})
try:
    with urllib.request.urlopen(req,timeout=15) as r:
        status=r.status
        body=r.read(65536).decode("utf-8","replace")
except Exception as e:
    print(json.dumps({"reachable":False,"error":type(e).__name__+":"+str(e)},sort_keys=True))
    raise
data=json.loads(body)
assert status==200,(status,body)
assert isinstance(data,dict),data
assert isinstance(data.get("busy"),bool),data
print(json.dumps({
  "reachable":True,
  "http_status":status,
  "busy":data.get("busy"),
  "mode":data.get("mode"),
  "started_at":data.get("started_at"),
  "job_id_present":bool(data.get("job_id")),
},sort_keys=True))
