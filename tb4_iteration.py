#!/usr/bin/env python3
from __future__ import annotations
import os, pathlib
import numpy as np
from PIL import Image

ROOT=pathlib.Path(os.environ["TASK_ENV"])
a=np.asarray(Image.open(ROOT/"data/layout.png").convert("RGB"))
mean=a.mean(axis=2);spread=a.max(axis=2)-a.min(axis=2)
mask=((mean<120)&(spread<22)).astype(np.uint8)
# Isolated unexplained central band from prior connected-component analysis.
x0,y0,x1,y1=270,385,555,500
m=mask[y0:y1,x0:x1]
cols=95; rows=38
# max-pool into textual pixels so thin glyph strokes survive.
ys=np.linspace(0,m.shape[0],rows+1,dtype=int)
xs=np.linspace(0,m.shape[1],cols+1,dtype=int)
lines=[]
for r in range(rows):
    row=[]
    for c in range(cols):
        block=m[ys[r]:ys[r+1],xs[c]:xs[c+1]]
        v=block.mean() if block.size else 0
        row.append("█" if v>=0.22 else ("▓" if v>=0.08 else ("░" if v>0 else " ")))
    lines.append("".join(row).rstrip())
print("TB4_LARGE_TEXT_ASCII_START")
for line in lines: print(line)
print("TB4_LARGE_TEXT_ASCII_END")
