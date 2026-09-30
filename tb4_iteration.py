#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, shutil, subprocess
import numpy as np
from PIL import Image

ROOT=pathlib.Path(os.environ["TASK_ENV"])
im=Image.open(ROOT/"data/layout.png").convert("RGB")
a=np.asarray(im)
mean=a.mean(axis=2)
spread=a.max(axis=2)-a.min(axis=2)
# Central neutral-dark typography only; exclude saturated illustration pixels.
mask=(mean<120)&(spread<22)
out=np.full(a.shape[:2],255,dtype=np.uint8)
out[mask]=0
# Crop only the already-localized typography zone, then upscale once.
crop=Image.fromarray(out[105:575,:]).resize((a.shape[1]*3,(575-105)*3),Image.Resampling.NEAREST)
path=pathlib.Path("/tmp/tb4_text_mask.png")
crop.save(path)
if shutil.which("tesseract") is None:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","tesseract-ocr"],check=True)
proc=subprocess.run(["tesseract",str(path),"stdout","-l","eng","--psm","6"],text=True,capture_output=True,check=True)
print("TB4_TEXT_OCR_START")
print(proc.stdout.strip())
print("TB4_TEXT_OCR_END")
