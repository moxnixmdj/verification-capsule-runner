from __future__ import annotations
import argparse, base64, hashlib, json, re, subprocess, time, urllib.request
from pathlib import Path
from PIL import Image
import yaml

TOOLS=[
  {
    "type":"function",
    "function":{
      "name":"crop",
      "description":"Crop the current chart to a smaller rectangle so labels, thin lines, and intersections can be inspected at higher effective resolution.",
      "parameters":{
        "type":"object",
        "properties":{
          "left":{"type":"integer"},
          "top":{"type":"integer"},
          "right":{"type":"integer"},
          "bottom":{"type":"integer"}
        },
        "required":["left","top","right","bottom"],
        "additionalProperties":False
      }
    }
  },
  {
    "type":"function",
    "function":{
      "name":"python",
      "description":"Measure the current chart offline using Python. /work/current_image.png is available with Pillow, NumPy, SciPy, Matplotlib, and OpenCV. Use this for axis calibration, pixel/color tracing, line/intersection detection, geometric measurement, or calculations. Print concise measurements only.",
      "parameters":{
        "type":"object",
        "properties":{"code":{"type":"string"}},
        "required":["code"],
        "additionalProperties":False
      }
    }
  }
]

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run_python(code:str,image:Path,workdir:Path):
    workdir.mkdir(parents=True,exist_ok=True)
    with Image.open(image) as im: im.save(workdir/"current_image.png")
    (workdir/"tool.py").write_text(code)
    cp=subprocess.run([
      "docker","run","--rm","--network","none","--read-only",
      "--cap-drop","ALL","--security-opt","no-new-privileges",
      "--pids-limit","64","--memory","768m","--cpus","1",
      "--tmpfs","/tmp:rw,nosuid,nodev,size=128m",
      "-v",f"{workdir.resolve()}:/work:rw","-w","/work",
      "brain-chartography-tool-v1","python","/work/tool.py"
    ],text=True,capture_output=True,timeout=90,env={"PATH":"/usr/local/bin:/usr/bin:/bin"})
    return {"returncode":cp.returncode,"stdout":cp.stdout[-6000:],"stderr":cp.stderr[-2000:]}

def request(server_url:str,image:Path,question:str,history:list,seed:int,require_tool:bool):
    with Image.open(image) as im:
        w,h=im.size; fmt=(im.format or "PNG").upper()
    mime={"PNG":"image/png","JPEG":"image/jpeg","JPG":"image/jpeg","WEBP":"image/webp"}.get(fmt,"image/png")
    uri="data:"+mime+";base64,"+base64.b64encode(image.read_bytes()).decode("ascii")
    hist=json.dumps(history[-6:],separators=(",",":"))
    prompt=(
      "Solve this professional chart-reading question from the image. "
      "Use measurements, not visual guessing. The available tools act on the CURRENT image. "
      f"Current image size is {w}x{h}. Prior tool results: {hist}. "
      "When measurements are sufficient, return only the substantive final answer with required units. "
      "QUESTION: "+question
    )
    payload={
      "temperature":0.0,"top_k":1,"top_p":1.0,"seed":seed,"max_tokens":384,
      "parallel_tool_calls":False,
      "tools":TOOLS,
      "tool_choice":"required" if require_tool else "auto",
      "messages":[{"role":"user","content":[
        {"type":"text","text":prompt},
        {"type":"image_url","image_url":{"url":uri}}
      ]}]
    }
    req=urllib.request.Request(server_url,data=json.dumps(payload,separators=(",",":")).encode(),
      headers={"Content-Type":"application/json"},method="POST")
    started=time.time()
    with urllib.request.urlopen(req,timeout=300) as resp: raw=resp.read()
    body=json.loads(raw)
    msg=body["choices"][0]["message"]
    calls=msg.get("tool_calls") or []
    content=(msg.get("content") or "").strip()
    receipt={"response_sha256":hashlib.sha256(raw).hexdigest(),"wall_seconds":round(time.time()-started,3),
             "finish_reason":body["choices"][0].get("finish_reason"),"tool_call_count":len(calls)}
    return content,calls,receipt

def parse_args(call):
    f=call.get("function") or {}
    name=f.get("name")
    args=f.get("arguments",{})
    if isinstance(args,str): args=json.loads(args)
    if not isinstance(args,dict): raise ValueError("TOOL_ARGS_NOT_OBJECT")
    return name,args

def solve(server_url:str,image:Path,question:str,workdir:Path,seed:int,max_tools=4):
    current=image; history=[]; receipts=[]
    for turn in range(max_tools+1):
        content,calls,rec=request(server_url,current,question,history,seed+turn,require_tool=(turn==0))
        receipts.append(rec)
        if calls:
            if len(calls)!=1:
                return {"status":"MULTIPLE_TOOL_CALLS","answer":"","history":history,"receipts":receipts}
            try: name,args=parse_args(calls[0])
            except Exception as e:
                return {"status":"BAD_TOOL_CALL","answer":"","error":type(e).__name__,"history":history,"receipts":receipts}
            if name=="crop":
                try:
                    l,t,r,b=[int(args[k]) for k in ("left","top","right","bottom")]
                except Exception:
                    return {"status":"BAD_CROP_ARGS","answer":"","history":history,"receipts":receipts}
                with Image.open(current) as im:
                    if l<0 or t<0 or r<=l or b<=t or r>im.width or b>im.height:
                        return {"status":"INVALID_CROP","answer":"","history":history,"receipts":receipts}
                    dst=workdir/f"crop_{turn}.png"; dst.parent.mkdir(parents=True,exist_ok=True)
                    im.crop((l,t,r,b)).save(dst)
                    out_size=list(Image.open(dst).size)
                history.append({"tool":"crop","box":[l,t,r,b],"output_size":out_size,"image_sha256":sha(dst)})
                current=dst
                continue
            if name=="python":
                code=str(args.get("code",""))
                if not code.strip(): return {"status":"EMPTY_PYTHON","answer":"","history":history,"receipts":receipts}
                try: tr=run_python(code,current,workdir/f"python_{turn}")
                except Exception as e:
                    return {"status":"PYTHON_TOOL_ERROR","answer":"","error":type(e).__name__,"history":history,"receipts":receipts}
                history.append({"tool":"python","code_sha256":hashlib.sha256(code.encode()).hexdigest(),**tr})
                continue
            return {"status":"UNKNOWN_TOOL","answer":"","history":history,"receipts":receipts}
        if turn==0:
            return {"status":"REQUIRED_TOOL_NOT_CALLED","answer":"","history":history,"receipts":receipts}
        if content:
            return {"status":"FINAL","answer":content,"history":history,"receipts":receipts}
        return {"status":"EMPTY_FINAL","answer":"","history":history,"receipts":receipts}
    return {"status":"TOOL_LIMIT","answer":"","history":history,"receipts":receipts}

def first_number(s):
    m=re.search(r"[-+]?\d[\d,]*(?:\.\d+)?",s)
    return float(m.group(0).replace(",","")) if m else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--official-root",required=True)
    ap.add_argument("--server-url",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.official_root)/"task_packs"/"sample_charts"; out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    specs=[("sample_task_1.yaml","sample_chart_1.png",(76.0,79.0)),
           ("sample_task_2.yaml","sample_chart_2.jpg",(330.0,370.0))]
    sealed=[]
    for i,(yf,img,rng) in enumerate(specs,1):
        y=yaml.safe_load((root/"tasks"/yf).read_text()); q=str(y["prompt"]).strip(); p=root/"charts"/img
        res=solve(a.server_url,p,q,out/f"case_{i}",910000+i*100)
        sealed.append({"case":i,"task_file":yf,"prompt_sha256":hashlib.sha256(q.encode()).hexdigest(),
                       "image_sha256":sha(p),"answer":res["answer"],"status":res["status"],"solver":res,
                       "acceptable":list(rng)})
    rp=out/"responses.json"; rp.write_text(json.dumps(sealed,indent=2,sort_keys=True)+"\n")
    rows=[]
    for x in sealed:
        v=first_number(x["answer"]); lo,hi=x["acceptable"]
        rows.append({"case":x["case"],"answer":x["answer"],"parsed_value":v,"acceptable":[lo,hi],
                     "pass":v is not None and lo<=v<=hi,"tool_history_len":len(x["solver"]["history"])})
    result={"schema":"PROJECT_BRAIN_CHARTOGRAPHY_QWEN8_NATIVE_REQUIRED_TOOLS_SAMPLE_V1",
      "response_set_sha256":sha(rp),"passed":sum(x["pass"] for x in rows),"total":2,"pass":all(x["pass"] for x in rows),
      "rows":rows,"heldout_cases_consumed":0,"heldout_gold_consumed":0,
      "native_function_calling":True,"first_turn_tool_choice":"required","image_min_tokens":1024,
      "incremental_spend_usd":0}
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__": main()
