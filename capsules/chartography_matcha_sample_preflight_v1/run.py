from __future__ import annotations
import urllib.request
from io import BytesIO
from PIL import Image
import torch
from transformers import Pix2StructForConditionalGeneration, Pix2StructProcessor

MODEL="google/matcha-chartqa"
REVISION="f36735077259b4b372763188832c72308c5cd223"
CHART_REF="3f1bf837232d3918c2cc35c6e2418c9e70d2a57b"
BASE=f"https://raw.githubusercontent.com/surge-ai/chartography/{CHART_REF}/task_packs/sample_charts/charts"

samples=[
 ("sample_1", f"{BASE}/sample_chart_1.png",
  "How long would it take an environment of 1100 degC / 0.03 K/m to deform 4 metres vertically. Answer in years with 1 decimal place"),
 ("sample_2", f"{BASE}/sample_chart_2.jpg",
  "Using Mg-9 wt % Al alloy, at what temperature does Mg17Al12 precipitate? Round to the nearest 10 degrees."),
]

processor=Pix2StructProcessor.from_pretrained(MODEL, revision=REVISION)
model=Pix2StructForConditionalGeneration.from_pretrained(MODEL, revision=REVISION)
model.eval()

for sid,url,q in samples:
    with urllib.request.urlopen(url, timeout=60) as r:
        image=Image.open(BytesIO(r.read())).convert("RGB")
    inputs=processor(images=image,text=q,return_tensors="pt")
    with torch.inference_mode():
        pred=model.generate(**inputs,max_new_tokens=128)
    ans=processor.decode(pred[0],skip_special_tokens=True).strip()
    safe=ans.replace("%","%25").replace("\r","%0D").replace("\n","%0A")
    print(f"::notice title=MatCha {sid}::{safe}")
    print(f"{sid}: {ans}")
print("MATCHA_CHARTOGRAPHY_PUBLIC_SAMPLE_PREFLIGHT_COMPLETE")
