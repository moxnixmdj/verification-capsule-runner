from __future__ import annotations
import json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from chartography_with_tools_adapter_v1 import run_with_tools

ROOT=Path(__file__).resolve().parents[2]
BIN=ROOT/"llama.cpp/build/bin/llama-mtmd-cli"
MODEL=ROOT/"model/model.gguf"
MMPROJ=ROOT/"model/mmproj.gguf"
calls=[]

def extract_action(stdout:str)->str:
    cands=re.findall(r'\{[^{}]*\}',stdout,re.S)
    for raw in reversed(cands):
        try:
            obj=json.loads(raw)
        except Exception:
            continue
        if isinstance(obj,dict) and (obj.get("tool")=="crop" or "final" in obj):
            return json.dumps(obj,separators=(",",":"))
    raise RuntimeError("NO_PARSEABLE_ACTION_JSON")

def infer(image_path:str,prompt:str,transcript:list[dict]):
    if not transcript:
        instruction=(
          'You are testing a crop tool protocol. Respond with JSON only. '
          'Your first and only allowed action now is exactly '
          '{"tool":"crop","left":16,"top":16,"right":48,"bottom":48}. '
          'Do not answer the question yet.'
        )
    else:
        instruction=(
          'You have received the cropped center region. Respond with JSON only in the form '
          '{"final":"ANSWER"}. Answer the question now.'
        )
    full=instruction+"\nQuestion: "+prompt
    cp=subprocess.run([
      str(BIN),"-m",str(MODEL),"--mmproj",str(MMPROJ),"--no-mmproj-offload",
      "--image",image_path,"-p",full,"-n","96","-t","4"
    ],capture_output=True,text=True,timeout=180)
    calls.append({"image":image_path,"returncode":cp.returncode,"stdout":cp.stdout[-8000:],"stderr":cp.stderr[-4000:]})
    if cp.returncode!=0:
        raise RuntimeError("MODEL_INFERENCE_FAILED")
    return extract_action(cp.stdout)

out=run_with_tools(ROOT/"synthetic.bmp","What color is the center square?",infer,workdir=ROOT/"out/crop-loop",max_crop_calls=2)
assert out["crop_calls"]==1,out
assert "blue" in out["answer"].lower(),out
result={"schema":"PROJECT_BRAIN_CHARTOGRAPHY_REAL_QWEN_CROP_LOOP_PREFLIGHT_V1","status":"PASS","terminal_cases_consumed":0,"incremental_spend_usd":0,"result":out,"model_calls":calls}
(ROOT/"out/real-qwen-crop-loop.json").write_text(json.dumps(result,indent=2))
print(json.dumps({"status":"PASS","answer":out["answer"],"crop_calls":out["crop_calls"]},sort_keys=True))
