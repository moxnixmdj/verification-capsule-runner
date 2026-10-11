from __future__ import annotations
import argparse, base64, hashlib, json, re, subprocess, time, urllib.request
from pathlib import Path
from PIL import Image
import yaml

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def _action(obj):
    if not isinstance(obj, dict):
        return None
    if set(obj)=={"final"} and isinstance(obj.get("final"),str) and obj["final"].strip():
        return {"kind":"final","answer":obj["final"].strip()}
    if set(obj)=={"tool","left","top","right","bottom"} and obj.get("tool")=="crop":
        vals=[obj[k] for k in ("left","top","right","bottom")]
        if all(type(v) is int for v in vals):
            return {"kind":"crop","box":tuple(vals)}
    if set(obj)=={"tool","code"} and obj.get("tool")=="python" and isinstance(obj.get("code"),str):
        return {"kind":"python","code":obj["code"]}
    return None

def parse_action(raw: str):
    dec=json.JSONDecoder()
    found=[]
    for i,ch in enumerate(raw):
        if ch!="{":
            continue
        try:
            obj,end=dec.raw_decode(raw[i:])
        except Exception:
            continue
        act=_action(obj)
        if act is not None:
            found.append((i,act))
    if found:
        return found[-1][1]
    lines=[x.strip() for x in raw.splitlines() if x.strip()]
    if lines:
        return {"kind":"final","answer":lines[-1]}
    return {"kind":"invalid"}

def run_python(code: str, image: Path, workdir: Path):
    workdir.mkdir(parents=True,exist_ok=True)
    with Image.open(image) as im:
        im.save(workdir/"current_image.png")
    (workdir/"tool.py").write_text(code)
    cp=subprocess.run([
        "docker","run","--rm","--network","none","--read-only",
        "--cap-drop","ALL","--security-opt","no-new-privileges",
        "--pids-limit","64","--memory","768m","--cpus","1",
        "--tmpfs","/tmp:rw,nosuid,nodev,size=128m",
        "-v",f"{workdir.resolve()}:/work:rw","-w","/work",
        "brain-chartography-tool-v1","python","/work/tool.py"
    ],text=True,capture_output=True,timeout=90,env={"PATH":"/usr/local/bin:/usr/bin:/bin"})
    return {"returncode":cp.returncode,"stdout":cp.stdout[-6000:],"stderr":cp.stderr[-2000:],
            "stdout_sha256":hashlib.sha256(cp.stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(cp.stderr.encode()).hexdigest()}

def invoke(server_url: str, image: Path, question: str, transcript: list, seed: int):
    with Image.open(image) as im:
        w,h=im.size; fmt=(im.format or "PNG").upper()
    history=[]
    for x in transcript[-6:]:
        if x["tool"]=="crop":
            history.append({"tool":"crop","box":x["box"],"output_size":x["output_size"]})
        else:
            history.append({"tool":"python","returncode":x["returncode"],"stdout":x["stdout"],"stderr":x["stderr"]})
    prompt=(
      "Solve this professional chart-reading question carefully. "
      "Use tools rather than eyeballing whenever numerical or geometric measurement can reduce ambiguity. "
      "Return exactly one compact JSON object. "
      "Crop: {\"tool\":\"crop\",\"left\":INT,\"top\":INT,\"right\":INT,\"bottom\":INT}. "
      "Python: {\"tool\":\"python\",\"code\":\"PYTHON CODE\"}. "
      "The Python tool is offline and can read /work/current_image.png with Pillow, NumPy, SciPy, Matplotlib and OpenCV. "
      "If tool measurements are decisive, follow them rather than contradicting them by visual guess. "
      f"Current image size is {w}x{h}. Tool history: {json.dumps(history,separators=(',',':'))}. "
      "When ready return {\"final\":\"ANSWER\"} with only the substantive answer and required units. "
      "QUESTION: "+question
    )
    mime={"PNG":"image/png","JPEG":"image/jpeg","JPG":"image/jpeg","WEBP":"image/webp"}.get(fmt,"image/png")
    uri="data:"+mime+";base64,"+base64.b64encode(image.read_bytes()).decode("ascii")
    payload={"temperature":0.1,"seed":seed,"max_tokens":256,
             "messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":uri}}]}]}
    req=urllib.request.Request(server_url,data=json.dumps(payload,separators=(",",":")).encode(),
                               headers={"Content-Type":"application/json"},method="POST")
    t=time.time()
    with urllib.request.urlopen(req,timeout=300) as resp:
        body_bytes=resp.read()
    body=json.loads(body_bytes)
    raw=str(body["choices"][0]["message"]["content"]).strip()
    return parse_action(raw),{"response_sha256":hashlib.sha256(body_bytes).hexdigest(),
                              "raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),
                              "wall_seconds":round(time.time()-t,3),"image_sha256":sha(image)}

def solve(server_url: str, image: Path, question: str, workdir: Path, seed: int, max_tools=5):
    current=image; transcript=[]; calls=[]
    for idx in range(max_tools+1):
        try:
            action,rec=invoke(server_url,current,question,transcript,seed+idx)
        except Exception as exc:
            return {"status":"MODEL_ERROR","answer":"","error_class":type(exc).__name__,"transcript":transcript,"calls":calls}
        calls.append(rec)
        if action["kind"]=="final":
            return {"status":"FINAL","answer":action["answer"],"transcript":transcript,"calls":calls}
        if idx>=max_tools:
            return {"status":"TOOL_LIMIT","answer":"","transcript":transcript,"calls":calls}
        if action["kind"]=="python":
            try:
                tool=run_python(action["code"],current,workdir/f"python_{idx}")
            except Exception as exc:
                return {"status":"PYTHON_TOOL_ERROR","answer":"","error_class":type(exc).__name__,"transcript":transcript,"calls":calls}
            transcript.append({"tool":"python","code_sha256":hashlib.sha256(action["code"].encode()).hexdigest(),**tool})
            continue
        if action["kind"]=="crop":
            l,t,r,b=action["box"]
            with Image.open(current) as im:
                if l<0 or t<0 or r<=l or b<=t or r>im.width or b>im.height:
                    return {"status":"INVALID_CROP","answer":"","transcript":transcript,"calls":calls}
                dst=workdir/f"crop_{idx}.png"; dst.parent.mkdir(parents=True,exist_ok=True)
                im.crop((l,t,r,b)).save(dst)
                size=list(Image.open(dst).size)
            transcript.append({"tool":"crop","box":[l,t,r,b],"output_size":size,"sha256":sha(dst)})
            current=dst
            continue
        return {"status":"INVALID_ACTION","answer":"","transcript":transcript,"calls":calls}
    return {"status":"NO_FINAL","answer":"","transcript":transcript,"calls":calls}

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
    specs=[("sample_task_1.yaml","sample_chart_1.png"),("sample_task_2.yaml","sample_chart_2.jpg")]
    responses=[]
    for i,(yf,img) in enumerate(specs,1):
        y=yaml.safe_load((root/"tasks"/yf).read_text()); q=str(y["prompt"]).strip(); p=root/"charts"/img
        res=solve(a.server_url,p,q,out/f"case_{i}",900000+i*100)
        responses.append({"case":i,"task_file":yf,"prompt_sha256":hashlib.sha256(q.encode()).hexdigest(),
                          "image_sha256":sha(p),"answer":res["answer"],"status":res["status"],"solver":res})
    rp=out/"responses.json"; rp.write_text(json.dumps(responses,indent=2,sort_keys=True)+"\n")
    # Development-sample grading happens only after both responses are sealed.
    gold=[]
    for yf,_ in specs:
        gold.append(str(yaml.safe_load((root/"tasks"/yf).read_text())["golden_answer"]))
    rows=[]
    ranges=[(76.0,79.0),(330.0,370.0)]
    for x,(lo,hi),g in zip(responses,ranges,gold):
        v=first_number(x["answer"])
        rows.append({"case":x["case"],"answer":x["answer"],"parsed_value":v,"acceptable":[lo,hi],
                     "golden_sha256":hashlib.sha256(g.encode()).hexdigest(),"pass":v is not None and lo<=v<=hi})
    result={"schema":"PROJECT_BRAIN_CHARTOGRAPHY_CHARTVERSE_OFFICIAL_SAMPLE_SERVER1024_V1",
            "response_set_sha256":sha(rp),"passed":sum(x["pass"] for x in rows),"total":2,"pass":all(x["pass"] for x in rows),
            "rows":rows,"heldout_cases_consumed":0,"heldout_gold_consumed":0,
            "image_min_tokens":1024,"persistent_server":True,
            "tool_surface":["isolated_python_scientific_stack","crop"],"incremental_spend_usd":0}
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__":
    main()
