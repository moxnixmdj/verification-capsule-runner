from __future__ import annotations
import json, urllib.request

URL="http://127.0.0.1:8080/v1/chat/completions"
payload={
  "model":"brain-qwen3.5-9b",
  "messages":[
    {"role":"system","content":"When a requested action has a provided tool, use the tool."},
    {"role":"user","content":"Call echo_tool with value exactly carrier_probe_20261003. Do not answer normally."}
  ],
  "tools":[{
    "type":"function",
    "function":{
      "name":"echo_tool",
      "description":"Echo one string value.",
      "parameters":{
        "type":"object",
        "properties":{"value":{"type":"string"}},
        "required":["value"],
        "additionalProperties":False
      }
    }
  }],
  "tool_choice":"required",
  "parallel_tool_calls":False,
  "temperature":0,
  "max_tokens":128,
  "stream":False
}
req=urllib.request.Request(
  URL,
  data=json.dumps(payload).encode(),
  headers={"Content-Type":"application/json"},
  method="POST",
)
with urllib.request.urlopen(req,timeout=180) as r:
  status=r.status
  body=r.read().decode("utf-8","replace")
data=json.loads(body)
assert status==200,(status,body)
choices=data.get("choices")
assert isinstance(choices,list) and choices,data
msg=choices[0].get("message") or {}
calls=msg.get("tool_calls")
assert isinstance(calls,list) and calls,data
matched=[]
for call in calls:
  fn=(call or {}).get("function") or {}
  if fn.get("name")!="echo_tool":
    continue
  args=fn.get("arguments")
  if isinstance(args,str):
    args=json.loads(args)
  assert isinstance(args,dict),fn
  matched.append(args)
assert matched,data
print(json.dumps({
  "openai_chat_completions_status":status,
  "tool_calls_present":True,
  "echo_tool_selected":True,
  "echo_arguments":matched[0],
  "finish_reason":choices[0].get("finish_reason"),
  "model":data.get("model"),
},sort_keys=True))
