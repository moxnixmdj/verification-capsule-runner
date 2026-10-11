#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import cv2
import numpy as np

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location("chartography_solver_v1",HERE/"solver_v1.py")
base=importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(base)

_old_group=base.group_ocr_lines


def group_ocr_lines_v2(words: list[dict]) -> list[dict]:
    native=_old_group(words)
    if not words:
        return native
    width=max(float(x["left"]+x["width"]) for x in words)
    height=max(float(x["top"]+x["height"]) for x in words)
    spatial=base.reconstruct_spatial_legend_rows(words,max(1,int(width)),max(1,int(height)))
    return spatial+native


def representative_legend_color_v2(img_bgr: np.ndarray, line: dict):
    h,w=img_bgr.shape[:2]
    x0=max(0,int(line["left"])-110)
    x1=max(x0+1,int(line["left"])-2)
    y0=max(0,int(line["cy"])-9)
    y1=min(h,int(line["cy"])+10)
    rgb=img_bgr[y0:y1,x0:x1,::-1].reshape(-1,3)
    mx=rgb.max(axis=1); mn=rgb.min(axis=1)
    pts=rgb[(mx-mn>40)&(mx<252)&(mx>55)]
    if len(pts)<3:
        raise RuntimeError("LEGEND_COLOR_NOT_FOUND")
    q=(pts//16).astype(int)
    keys=q[:,0]*256+q[:,1]*16+q[:,2]
    vals,counts=np.unique(keys,return_counts=True)
    bucket=pts[keys==vals[np.argmax(counts)]]
    return np.median(bucket,axis=0).astype(float)


def classify_line_style(sig: dict) -> str:
    coverage=float(sig.get("coverage",0.0))
    med=float(sig.get("median_run",0.0))
    mx=float(sig.get("max_run",0.0))
    rc=int(sig.get("run_count",0))
    span=max(1,int(sig.get("span",1)))
    if coverage>=0.82 or (rc<=2 and mx/span>=0.60):
        return "solid"
    if med<=5.0 and mx<=10.0 and coverage<=0.58:
        return "dotted"
    return "dashed"


def legend_style_signature_v2(img_bgr: np.ndarray, line: dict, target_rgb: np.ndarray) -> dict:
    h,w=img_bgr.shape[:2]
    x0=max(0,int(line["left"])-110)
    x1=max(x0+1,int(line["left"])-2)
    y0=max(0,int(line["cy"])-9)
    y1=min(h,int(line["cy"])+10)
    rgb=img_bgr[y0:y1,x0:x1,::-1].astype(float)
    dist=np.linalg.norm(rgb-target_rgb.reshape(1,1,3),axis=2)
    present=np.any(dist<70,axis=0)
    idx=np.flatnonzero(present)
    if len(idx):
        present=present[idx[0]:idx[-1]+1]
    runs=base._runs(present)
    sig={
        "coverage":float(np.mean(present)) if len(present) else 0.0,
        "median_run":float(np.median(runs)) if runs else 0.0,
        "max_run":int(max(runs)) if runs else 0,
        "run_count":len(runs),
        "span":int(len(present)),
    }
    sig["class"]=classify_line_style(sig)
    return sig


def cluster_same_color_lines_v2(
    xx: np.ndarray, yy: np.ndarray, xfit: dict, yfit: dict, target_style: dict
) -> dict:
    xd=base.px_to_data(xx,xfit)
    yd=base.px_to_data(yy,yfit)
    xvals=np.array([v for _,v,_ in xfit["inliers"]],float)
    yvals=np.array([v for _,v,_ in yfit["inliers"]],float)
    xmin=float(np.min(xvals)); xmax=float(np.max(xvals))
    ymin=float(np.min(yvals)); ymax=float(np.max(yvals))
    xspan=max(xmax-xmin,1e-9); yspan=max(ymax-ymin,1e-9)

    keep=(
        (xd>xmin+0.18*xspan)&(xd<=xmax+0.04*xspan)
        &(yd>=ymin-0.08*yspan)&(yd<=ymax+0.08*yspan)
    )
    xx2=xx[keep]; xd2=xd[keep]; yd2=yd[keep]
    if len(xd2)<60:
        raise RuntimeError("COLORED_CURVE_CLUSTER_PIXELS_INSUFFICIENT")

    ratio=(yd2/np.maximum(xd2,1e-9)).astype(np.float32)
    lo,hi=np.percentile(ratio,[2,98])
    good=(ratio>=lo)&(ratio<=hi)
    ratio=ratio[good]; xx2=xx2[good]; xd2=xd2[good]; yd2=yd2[good]
    if len(ratio)<60:
        raise RuntimeError("COLORED_CURVE_RATIO_PIXELS_INSUFFICIENT")

    K=3 if len(ratio)>=120 else 2
    criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,100,1e-7)
    _,labels,centers=cv2.kmeans(ratio.reshape(-1,1),K,None,criteria,20,cv2.KMEANS_PP_CENTERS)
    labels=labels.ravel(); centers=centers.ravel()
    target_class=target_style.get("class") or classify_line_style(target_style)
    candidates=[]

    for ci in range(K):
        sel=labels==ci
        if np.count_nonzero(sel)<15:
            continue
        xdc=xd2[sel]; ydc=yd2[sel]; xpc=xx2[sel].astype(int)
        a,b=np.polyfit(xdc,ydc,1)
        p0=float(a*xmin+b); p1=float(a*xmax+b)
        margin=0.15*yspan
        if a<=0 or a>1.5*yspan/xspan:
            continue
        if not (ymin-margin<=p0<=ymax+margin and ymin-margin<=p1<=ymax+margin):
            continue

        lo_px=int(np.min(xpc)); hi_px=int(np.max(xpc))
        present=np.zeros(max(1,hi_px-lo_px+1),dtype=bool)
        present[np.unique(xpc)-lo_px]=True
        runs=base._runs(present)
        sig={
            "coverage":float(np.mean(present)),
            "median_run":float(np.median(runs)) if runs else 0.0,
            "max_run":int(max(runs)) if runs else 0,
            "run_count":len(runs),
            "span":int(len(present)),
        }
        sig["class"]=classify_line_style(sig)
        residual=float(np.mean(np.abs(ydc-(a*xdc+b))))/yspan
        class_penalty=0.0 if sig["class"]==target_class else 10.0
        score=class_penalty+abs(sig["coverage"]-float(target_style.get("coverage",0)))+residual
        candidates.append({
            "slope":float(a),"intercept":float(b),"style":sig,
            "style_distance":float(score),"center_ratio":float(centers[ci]),
            "support":int(np.count_nonzero(sel)),"predicted_edge_values":[p0,p1],
        })
    if not candidates:
        raise RuntimeError("NO_PLAUSIBLE_COLORED_LINE_CLUSTERS")
    exact=[x for x in candidates if x["style"]["class"]==target_class]
    pool=exact if exact else candidates
    return min(pool,key=lambda x:(x["style_distance"],-x["support"]))


base.group_ocr_lines=group_ocr_lines_v2
base.representative_legend_color=representative_legend_color_v2
base.legend_style_signature=legend_style_signature_v2
base.cluster_same_color_lines=cluster_same_color_lines_v2

solve=base.solve


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True)
    ap.add_argument("--question",required=True)
    ap.add_argument("--out")
    a=ap.parse_args()
    result=solve(Path(a.image),a.question)
    payload=json.dumps(result,sort_keys=True)
    print(payload)
    if a.out:
        Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    raise SystemExit(0 if result["status"]=="FINAL" else 2)

if __name__=="__main__":
    main()
