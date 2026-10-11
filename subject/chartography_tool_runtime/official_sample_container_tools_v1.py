from __future__ import annotations

import argparse, hashlib, json, re, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image
import yaml

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_action(raw: str):
    lines=[x.strip() for x in raw.splitlines() if x.strip()]
    for line in reversed(lines):
        try:
            obj=json.loads(line)
        except Exception:
            continue
        if isinstance(obj,dict) and set(obj)=={"final"} and isinstance(obj["final"],str) and obj["final"].strip():
            return {"kind":"final","answer":obj["final"].strip()}
        if isinstance(obj,dict) and set(obj)=={"tool","left","top","right","bottom"} and obj.get("tool")=="crop":
            vals=[obj[k] for k in ("left","top","right","bottom")]
            if all(type(v) is int for v in vals):
                return {"kind":"crop","box":tuple(vals)}
        if isinstance(obj,dict) and set(obj)=={"tool","code"} and obj.get("tool")=="python" and isinstance(obj.get("code"),str):
            return {"kind":"python","code":obj["code"]}
    return {"kind":"invalid"}

def run_python_tool(code: str, current_image: Path, tool_dir: Path):
    tool_dir.mkdir(parents=True,exist_ok=True)
    image_copy=tool_dir/"current_image.png"
    with Image.open(current_image) as im:
        im.save(image_copy)
    code_path=tool_dir/"tool.py"
    code_path.write_text(code)
    cp=subprocess.run([
        "docker","run","--rm","--network","none","--read-only",
        "--memory","768m","--cpus","1",
        "--tmpfs","/tmp:rw,nosuid,nodev,size=128m",
        "-v",f"{tool_dir.resolve()}:/work:rw",
        "-w","/work","brain-chartography-tool-v1",
        "python","/work/tool.py"
    ],text=True,capture_output=True,timeout=90,env={"PATH":shutil.which("docker").rsplit("/",1)[0]+":/usr/bin:/bin"})
    return {
        "returncode":cp.returncode,
        "stdout":cp.stdout[-6000:],
        "stderr":cp.stderr[-2000:],
        "stdout_sha256":hashlib.sha256(cp.stdout.encode()).hexdigest(),
        "stderr_sha256":hashlib.sha256(cp.stderr.encode()).hexdigest(),
    }

def invoke(cli:Path,model:Path,mmproj:Path,image:Path,question:str,transcript:list,seed:int,timeout:int):
    with Image.open(image) as im:
        w,h=im.size
    prior=[]
    for x in transcript[-6:]:
        if x["tool"]=="crop":
            prior.append({"tool":"crop","box":x["box"],"result_image_size":x["result_image_size"]})
        elif x["tool"]=="python":
            prior.append({"tool":"python","returncode":x["returncode"],"stdout":x["stdout"],"stderr":x["stderr"]})
    prompt=(
        "Solve one professional chart-reading question. You have the CURRENT chart image plus two tools. "
        "Return exactly ONE compact JSON object on the final output line. "
        "Crop: {\"tool\":\"crop\",\"left\":INT,\"top\":INT,\"right\":INT,\"bottom\":INT}. "
        "Python: {\"tool\":\"python\",\"code\":\"PYTHON CODE\"}. "
        "The Python tool runs offline in an isolated container. It can read /work/current_image.png and has "
        "Python 3, Pillow, NumPy, SciPy, Matplotlib, and OpenCV. Print only measurements you need. "
        "It cannot access the benchmark, network, credentials, or other files. "
        "When ready return {\"final\":\"ANSWER\"}. Preserve units required by the question. "
        f"Current image size: {w}x{h}. Tool history: {json.dumps(prior,separators=(',',':'))}. "
        f"QUESTION: {question}"
    )
    cp=subprocess.run([
        str(cli),"-m",str(model),"--mmproj",str(mmproj),"--no-mmproj-offload",
        "--image",str(image),"-p",prompt,"-n","256","-t","4",
        "--seed",str(seed),"--temp","0.1","--image-min-tokens","256"
    ],text=True,capture_output=True,timeout=timeout)
    return parse_action(cp.stdout),{
        "returncode":cp.returncode,
        "stdout_sha256":hashlib.sha256(cp.stdout.encode()).hexdigest(),
        "stderr_sha256":hashlib.sha256(cp.stderr.encode()).hexdigest(),
        "image_sha256":sha(image),
    }

def solve(cli,model,mmproj,image,question,workdir,seed,timeout=300,max_tools=5):
    current=Path(image)
    workdir.mkdir(parents=True,exist_ok=True)
    transcript=[]; calls=[]
    for idx in range(max_tools+1):
        action,receipt=invoke(cli,model,mmproj,current,question,transcript,seed+idx,timeout)
        calls.append(receipt)
        if receipt["returncode"]!=0:
            return {"status":"MODEL_ERROR","answer":"","transcript":transcript,"calls":calls}
        if action["kind"]=="final":
            return {"status":"FINAL","answer":action["answer"],"transcript":transcript,"calls":calls}
        if idx>=max_tools:
            return {"status":"TOOL_LIMIT","answer":"","transcript":transcript,"calls":calls}
        if action["kind"]=="crop":
            l,t,r,b=action["box"]
            with Image.open(current) as im:
                if l<0 or t<0 or r<=l or b<=t or r>im.width or b>im.height:
                    return {"status":"INVALID_CROP","answer":"","transcript":transcript,"calls":calls}
                dst=workdir/f"crop_{idx}.png"
                im.crop((l,t,r,b)).save(dst)
                size=list(Image.open(dst).size)
            transcript.append({"tool":"crop","box":[l,t,r,b],"result_image_size":size,"sha256":sha(dst)})
            current=dst
            continue
        if action["kind"]=="python":
            rec=run_python_tool(action["code"],current,workdir/f"python_{idx}")
            transcript.append({"tool":"python","code_sha256":hashlib.sha256(action["code"].encode()).hexdigest(),**rec})
            continue
        return {"status":"INVALID_ACTION","answer":"","transcript":transcript,"calls":calls}
    return {"status":"NO_FINAL","answer":"","transcript":transcript,"calls":calls}

def first_number(s):
    m=re.search(r"[-+]?\d[\d,]*(?:\.\d+)?",s)
    return float(m.group(0).replace(",","")) if m else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--official-root",required=True)
    ap.add_argument("--cli",required=True)
    ap.add_argument("--model",required=True)
    ap.add_argument("--mmproj",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.official_root)/"task_packs"/"sample_charts"
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    specs=[
        ("sample_task_1.yaml","sample_chart_1.png",76.0,79.0),
        ("sample_task_2.yaml","sample_chart_2.jpg",330.0,370.0),
    ]
    responses=[]
    for i,(yaml_name,img_name,lo,hi) in enumerate(specs,1):
        y=yaml.safe_load((root/"tasks"/yaml_name).read_text())
        prompt=str(y["prompt"]).strip()
        image=root/"charts"/img_name
        res=solve(Path(a.cli),Path(a.model),Path(a.mmproj),image,prompt,out/f"case_{i}",810000+i*100)
        responses.append({
            "case":i,"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
            "image_sha256":sha(image),"answer":res["answer"],"status":res["status"],
            "solver":res,"acceptable":[lo,hi]
        })

    sealed=out/"responses.json"
    sealed.write_text(json.dumps(responses,indent=2,sort_keys=True)+"\n")
    response_sha=sha(sealed)

    rows=[]
    for x in responses:
        v=first_number(x["answer"])
        lo,hi=x["acceptable"]
        rows.append({"case":x["case"],"answer":x["answer"],"parsed_value":v,"pass":v is not None and lo<=v<=hi})
    result={
        "schema":"PROJECT_BRAIN_CHARTOGRAPHY_CHARTVERSE_OFFICIAL_SAMPLE_CONTAINER_TOOLS_V1",
        "response_set_sha256":response_sha,
        "passed":sum(x["pass"] for x in rows),"total":2,"pass":all(x["pass"] for x in rows),
        "rows":rows,
        "heldout_cases_consumed":0,"heldout_gold_consumed":0,
        "tool_surface":["isolated_python_container","crop"],
        "python_container_network":"NONE",
        "incremental_spend_usd":0
    }
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__":
    main()
