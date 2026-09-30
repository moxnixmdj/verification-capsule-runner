#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib
import cv2, numpy as np
from PIL import Image

ROOT=pathlib.Path(os.environ["TASK_ENV"])
T=np.asarray(Image.open(ROOT/"data/layout.png").convert("RGB"))
C=np.asarray(Image.open(ROOT/"data/components/component_5.png").convert("RGBA"))
COLORS=[(252,100,93),(252,100,94),(245,137,86),(205,57,59),(255,189,91),(236,86,82)]

def diag(arr,color,alpha=None):
    mask=np.all(arr[...,:3]==np.array(color,dtype=arr.dtype),axis=2)
    if alpha is not None: mask &= alpha>0
    ys,xs=np.where(mask)
    out={"count":int(mask.sum())}
    if len(xs):
      out["bbox"]=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
      out["centroid"]=[float(xs.mean()),float(ys.mean())]
      n,lab,stats,cents=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
      comps=[]
      for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area<4:continue
        comps.append({"bbox":[int(x),int(y),int(x+w),int(y+h)],"area":int(area),
                      "centroid":[float(cents[i][0]),float(cents[i][1])]})
      comps.sort(key=lambda x:-x["area"])
      out["components"]=comps[:20]
    return out

out={"target":{},"component5":{}}
for c in COLORS:
    k=",".join(map(str,c))
    out["target"][k]=diag(T,c)
    out["component5"][k]=diag(C,c,C[...,3])
print("TB4_COLOR_GEOMETRY_START")
print(json.dumps(out,sort_keys=True))
print("TB4_COLOR_GEOMETRY_END")
