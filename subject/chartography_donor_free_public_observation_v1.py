from __future__ import annotations
import json, subprocess, csv, io, hashlib
from pathlib import Path
from collections import Counter
from PIL import Image

ROOT=Path("official/task_packs/sample_charts")
CASES=[ROOT/"charts"/"sample_chart_1.png", ROOT/"charts"/"sample_chart_2.jpg"]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def tsv(path):
    cp=subprocess.run(["tesseract",str(path),"stdout","-l","eng","--psm","6","tsv"],text=True,capture_output=True,check=True)
    rows=[]
    for r in csv.DictReader(io.StringIO(cp.stdout),delimiter="\t"):
        txt=(r.get("text") or "").strip()
        if not txt: continue
        try: conf=float(r.get("conf") or -1)
        except: conf=-1
        rows.append({
          "text":txt,"conf":conf,
          "left":int(r["left"]),"top":int(r["top"]),
          "width":int(r["width"]),"height":int(r["height"]),
          "block":int(r["block_num"]),"par":int(r["par_num"]),"line":int(r["line_num"]),"word":int(r["word_num"])
        })
    return rows

def color_summary(path):
    im=Image.open(path).convert("RGB")
    # quantize to 32-level bins; retain saturated/non-white colors useful for chart series
    bins=Counter()
    dark=0
    for p in im.getdata():
        if max(p)<=90 and max(p)-min(p)<=35: dark+=1
        if max(p)-min(p)>=45 and max(p)<=250:
            q=tuple((v//32)*32 for v in p)
            bins[q]+=1
    return {
      "size":list(im.size),
      "dark_pixels":dark,
      "top_saturated_bins":[[list(k),v] for k,v in bins.most_common(20)]
    }

out={"schema":"PROJECT_BRAIN_CHARTOGRAPHY_PUBLIC_ZERO_MODEL_OBSERVATION_V1","cases":[],"heldout_cases_consumed":0,"model_calls":0}
for p in CASES:
    rows=tsv(p)
    out["cases"].append({
      "file":p.name,"sha256":sha(p),"ocr_words":rows,"color_summary":color_summary(p)
    })
Path("out").mkdir(exist_ok=True)
Path("out/observation.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps(out,sort_keys=True))
