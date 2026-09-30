#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib
import cv2, numpy as np
from PIL import Image

ROOT=pathlib.Path(os.environ["TASK_ENV"])
T=np.asarray(Image.open(ROOT/"data/layout.png").convert("RGB"))
gray=np.max(T,axis=2)-np.min(T,axis=2)
# neutral/dark candidate typography; ignore saturated illustration pixels
mask=(T.mean(axis=2)<105) & (gray<18)
raw=mask.astype(np.uint8)
# close glyph fragments and group into line/word-scale regions
dil=cv2.dilate(raw,cv2.getStructuringElement(cv2.MORPH_RECT,(11,3)),iterations=1)
dil=cv2.morphologyEx(dil,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(5,3)))
n,lab,stats,cents=cv2.connectedComponentsWithStats(dil,8)
regions=[]
for i in range(1,n):
    x,y,w,h,area=stats[i]
    original=int(raw[y:y+h,x:x+w].sum())
    if original<8 or w<3 or h<3:continue
    regions.append({"bbox":[int(x),int(y),int(x+w),int(y+h)],"dilated_area":int(area),
                    "dark_pixels":original,"centroid":[float(cents[i][0]),float(cents[i][1])]})
regions.sort(key=lambda r:(r["bbox"][1],r["bbox"][0]))

colors={}
for c in [(53,53,54),(34,34,33)]:
    m=np.all(T==np.array(c,dtype=np.uint8),axis=2)
    ys,xs=np.where(m)
    colors[str(c)]={"count":int(m.sum()),"bbox":None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]}

# horizontal projections by row to reveal text bands
row=raw.sum(axis=1)
bands=[];start=None
for y,v in enumerate(row):
    if v>=3 and start is None:start=y
    if (v<3 or y==len(row)-1) and start is not None:
        end=y if v<3 else y+1
        if end-start>=2:
            bands.append({"y0":start,"y1":end,"dark_pixels":int(row[start:end].sum()),"max_row":int(row[start:end].max())})
        start=None

print("TB4_TEXT_GEOMETRY_START")
print(json.dumps({"neutral_dark_pixels":int(raw.sum()),"regions":regions,"bands":bands,"exact_colors":colors},sort_keys=True))
print("TB4_TEXT_GEOMETRY_END")
