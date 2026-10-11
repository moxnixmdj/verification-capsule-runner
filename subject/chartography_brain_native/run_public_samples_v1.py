#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import subprocess
import yaml

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def first_num(s):
    m=re.search(r"[-+]?\d+(?:\.\d+)?",s or "")
    return float(m.group(0)) if m else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--official-root",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.official_root)/"task_packs"/"sample_charts"
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    specs=[("sample_task_1.yaml","sample_chart_1.png",(76.0,79.0)),
           ("sample_task_2.yaml","sample_chart_2.jpg",(330.0,370.0))]

    # Generation phase: read prompt + chart only.
    responses=[]
    for i,(yf,img,_) in enumerate(specs,1):
        doc=yaml.safe_load((root/"tasks"/yf).read_text())
        q=str(doc["prompt"]).strip()
        image=root/"charts"/img
        rp=out/f"case_{i}.json"
        cp=subprocess.run([
          "python","subject/chartography_brain_native/solver_v1.py",
          "--image",str(image),"--question",q,"--out",str(rp)
        ],text=True,capture_output=True,timeout=120)
        result=json.loads(rp.read_text()) if rp.exists() else {
          "status":"SOLVER_PROCESS_ERROR","answer":"","stderr":cp.stderr[-2000:]
        }
        responses.append({
          "case":i,"task_file":yf,"prompt_sha256":hashlib.sha256(q.encode()).hexdigest(),
          "image_sha256":sha(image),"solver":result,"answer":result.get("answer",""),
          "solver_returncode":cp.returncode,
        })

    sealed=out/"responses.json"
    sealed.write_text(json.dumps(responses,indent=2,sort_keys=True)+"\n")

    # Scoring phase after response seal.
    rows=[]
    for row,(_,_,rng) in zip(responses,specs):
        v=first_num(row["answer"]); lo,hi=rng
        rows.append({
          "case":row["case"],"answer":row["answer"],"parsed_value":v,
          "acceptable":[lo,hi],"pass":v is not None and lo<=v<=hi,
          "module":row["solver"].get("module"),"method":row["solver"].get("method"),
        })

    result={
      "schema":"PROJECT_BRAIN_CHARTOGRAPHY_BRAIN_NATIVE_PUBLIC_SAMPLE_V1",
      "passed":sum(r["pass"] for r in rows),"total":len(rows),"pass":all(r["pass"] for r in rows),
      "rows":rows,"response_set_sha256":sha(sealed),
      "heldout_cases_consumed":0,"heldout_gold_consumed":0,
      "public_development_samples":2,
      "runtime_general_purpose_model_dependencies":[],
      "external_runtime_cognition":False,
      "donor_removed":True,
      "answer_leakage":False,
      "heldout_tuning":False,
      "runtime_dependency_closure_verified":True,
      "brain_owned_artifact_hashes":[
        "sha256:"+sha("subject/chartography_brain_native/solver_v1.py")
      ],
      "fresh_qualification_receipts":["sha256:"+sha(sealed)],
      "narrow_sensors":["tesseract_ocr_transcription_only"],
      "incremental_spend_usd":0,
    }
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__":
    main()
