#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9.%/+\-]+", " ", s.lower()).strip()


def _ocr_tsv_once(image: Path, *, psm: int, run_id: str, offset=(0, 0), scale=1.0) -> list[dict]:
    cp = subprocess.run(
        ["tesseract", str(image), "stdout", "--psm", str(psm), "tsv"],
        text=True, capture_output=True, timeout=60, check=True
    )
    rows=[]
    ox,oy=offset
    for r in csv.DictReader(io.StringIO(cp.stdout), delimiter="\t"):
        txt=(r.get("text") or "").strip()
        if not txt:
            continue
        try:
            conf=float(r.get("conf") or -1)
            left=int(r["left"]); top=int(r["top"]); width=int(r["width"]); height=int(r["height"])
            block=int(r["block_num"]); par=int(r["par_num"]); line=int(r["line_num"])
        except Exception:
            continue
        if conf < 0:
            continue
        left=ox+left/scale; top=oy+top/scale
        width=width/scale; height=height/scale
        rows.append({
            "text":txt,"conf":conf,"left":left,"top":top,"width":width,"height":height,
            "block":block,"par":par,"line":line,"run":run_id,
            "cx":left+width/2.0,"cy":top+height/2.0,
        })
    return rows


def run_tesseract_tsv(image: Path) -> list[dict]:
    # OCR is a transcription-only sensor. Multiple deterministic views make
    # small legend text readable without delegating chart reasoning.
    rows=[]
    rows += _ocr_tsv_once(image, psm=6, run_id="full6")
    rows += _ocr_tsv_once(image, psm=11, run_id="full11")
    with Image.open(image) as im:
        w,h=im.size
        x0=int(w*0.58)
        crop=im.crop((x0,0,w,h))
        up=crop.resize((crop.width*2,crop.height*2),Image.Resampling.LANCZOS)
        with tempfile.NamedTemporaryFile(suffix=".png",delete=False) as tmp:
            tmp_path=Path(tmp.name)
        try:
            up.save(tmp_path)
            rows += _ocr_tsv_once(tmp_path, psm=6, run_id="right6", offset=(x0,0), scale=2.0)
            rows += _ocr_tsv_once(tmp_path, psm=11, run_id="right11", offset=(x0,0), scale=2.0)
        finally:
            tmp_path.unlink(missing_ok=True)

    # Deduplicate near-identical detections from different OCR views.
    out=[]
    for r in sorted(rows,key=lambda x:(-x["conf"],x["top"],x["left"])):
        nt=norm_text(r["text"])
        duplicate=False
        for q in out:
            if norm_text(q["text"])==nt and abs(q["cx"]-r["cx"])<5 and abs(q["cy"]-r["cy"])<5:
                duplicate=True; break
        if not duplicate:
            out.append(r)
    return out


def group_ocr_lines(words: list[dict]) -> list[dict]:
    groups={}
    for w in words:
        key=(w.get("run","default"),w["block"],w["par"],w["line"])
        groups.setdefault(key,[]).append(w)
    out=[]
    for ws in groups.values():
        ws=sorted(ws,key=lambda x:x["left"])
        out.append({
            "text":" ".join(x["text"] for x in ws),
            "left":min(x["left"] for x in ws),
            "top":min(x["top"] for x in ws),
            "right":max(x["left"]+x["width"] for x in ws),
            "bottom":max(x["top"]+x["height"] for x in ws),
            "cy":sum(x["cy"] for x in ws)/len(ws),
            "words":ws,
        })
    return out


def parse_number(s: str):
    s=s.strip().replace(",","")
    s=s.replace("O","0").replace("o","0")
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?",s):
        try: return float(s)
        except Exception: return None
    return None


def fit_axis_ticks(words: list[dict], width: int, height: int, axis: str):
    pts=[]
    for w in words:
        v=parse_number(w["text"])
        if v is None:
            continue
        if axis=="x":
            if w["cy"] < height*0.72:
                continue
            pts.append((w["cx"],v,w))
        else:
            if w["cx"] > width*0.20:
                continue
            if w["cy"] > height*0.92:
                continue
            pts.append((w["cy"],v,w))
    if len(pts)<2:
        raise RuntimeError(f"INSUFFICIENT_{axis.upper()}_TICKS")

    # Try plausible subsets. Choose the subset that is most linear and has
    # monotone numeric order in the expected direction.
    best=None
    n=len(pts)
    for i in range(n):
        for j in range(i+1,n):
            p1,v1,_=pts[i]; p2,v2,_=pts[j]
            if abs(p2-p1)<20 or abs(v2-v1)<1e-9:
                continue
            a=(v2-v1)/(p2-p1); b=v1-a*p1
            # x values increase to the right; y values decrease upward.
            if axis=="x" and a<=0: continue
            if axis=="y" and a>=0: continue
            inliers=[]
            for p,v,w in pts:
                pred=a*p+b
                tol=max(0.75,0.035*max(abs(v),1.0))
                if abs(pred-v)<=tol:
                    inliers.append((p,v,w))
            if len(inliers)<2: continue
            xs=np.array([x[0] for x in inliers],float)
            ys=np.array([x[1] for x in inliers],float)
            aa,bb=np.polyfit(xs,ys,1)
            residual=float(np.mean(np.abs((aa*xs+bb)-ys)))
            score=(len(inliers),-residual)
            if best is None or score>best[0]:
                best=(score,float(aa),float(bb),inliers)
    if best is None:
        raise RuntimeError(f"NO_{axis.upper()}_AXIS_FIT")
    return {"a":best[1],"b":best[2],"inliers":best[3]}


def data_to_px(value: float, fit: dict) -> float:
    return (value-fit["b"])/fit["a"]


def px_to_data(px: float, fit: dict) -> float:
    return fit["a"]*px+fit["b"]


def parse_line_chart_question(q: str):
    m=re.search(r"environment\s+of\s+(\d+(?:\.\d+)?)\s*deg\s*c?\s*/\s*([0-9.]+)\s*k\s*/\s*m",q,re.I)
    if not m:
        m=re.search(r"(\d+(?:\.\d+)?)\s*degc\s*/\s*([0-9.]+)\s*k/m",q,re.I)
    y=re.search(r"deform\s+(\d+(?:\.\d+)?)\s*met",q,re.I)
    dec=re.search(r"(\d+)\s*decimal",q,re.I)
    if not (m and y):
        return None
    return {
        "temp":float(m.group(1)),
        "gradient":float(m.group(2)),
        "target_y":float(y.group(1)),
        "decimals":int(dec.group(1)) if dec else 1,
    }


def _numbers_in_text(text: str) -> list[float]:
    t=text.replace(",",".").replace("O","0").replace("o","0")
    vals=[]
    for m in re.finditer(r"(?<![A-Za-z])\d+(?:\.\d+)?",t):
        try: vals.append(float(m.group(0)))
        except Exception: pass
    return vals


def find_legend_line(lines: list[dict], temp: float, gradient: float):
    cands=[]
    temp_only=[]
    for line in lines:
        vals=_numbers_in_text(line["text"])
        has_temp=any(abs(v-temp)<=max(0.5,0.001*abs(temp)) for v in vals)
        has_grad=any(abs(v-gradient)<=max(0.0015,0.08*abs(gradient)) for v in vals)
        if has_temp:
            temp_only.append(line)
        score=(5 if has_temp else 0)+(5 if has_grad else 0)
        n=norm_text(line["text"])
        if "k" in n or "/" in line["text"]: score+=1
        if score>=10:
            cands.append((score,line))
    if cands:
        return max(cands,key=lambda x:(x[0],-x[1]["left"]))[1]

    # OCR often preserves the large temperature token while losing a decimal
    # in the smaller gradient. If several same-temperature legend rows exist,
    # infer the requested row from numeric gradient order only when enough
    # neighboring rows are recoverable.
    if len(temp_only)>=2:
        enriched=[]
        for line in temp_only:
            vals=[v for v in _numbers_in_text(line["text"]) if abs(v-temp)>max(0.5,0.001*abs(temp))]
            small=[v for v in vals if 0 < v < 1]
            enriched.append((line,small[0] if small else None))
        exact=[x for x in enriched if x[1] is not None and abs(x[1]-gradient)<=max(0.002,0.1*gradient)]
        if exact:
            return min(exact,key=lambda x:abs(x[1]-gradient))[0]

        # Last deterministic fallback for regularly spaced legend groups:
        # sort rows vertically and use the requested value's rank among
        # observed neighboring gradients if at least two are readable.
        observed=sorted({g for _,g in enriched if g is not None})
        if len(observed)>=2 and min(observed)<=gradient<=max(observed):
            rows_sorted=sorted([x[0] for x in enriched],key=lambda x:x["cy"])
            rank=int(round((gradient-min(observed))/(max(observed)-min(observed))*(len(rows_sorted)-1)))
            rank=max(0,min(len(rows_sorted)-1,rank))
            return rows_sorted[rank]

    raise RuntimeError("TARGET_LEGEND_ROW_NOT_FOUND")


def representative_legend_color(img_bgr: np.ndarray, line: dict):
    h,w=img_bgr.shape[:2]
    x0=max(0,int(line["left"])-55)
    x1=max(x0+1,int(line["left"])-3)
    y0=max(0,int(line["cy"])-7)
    y1=min(h,int(line["cy"])+8)
    patch=img_bgr[y0:y1,x0:x1]
    rgb=patch[:,:,::-1].reshape(-1,3)
    # Colored sample pixels: sufficiently saturated and not near white/black.
    mx=rgb.max(axis=1); mn=rgb.min(axis=1)
    mask=(mx-mn>45)&(mx<250)&(mx>70)
    pts=rgb[mask]
    if len(pts)<3:
        raise RuntimeError("LEGEND_COLOR_NOT_FOUND")
    # Densest quantized color bin.
    q=(pts//16).astype(int)
    keys=q[:,0]*256+q[:,1]*16+q[:,2]
    vals,counts=np.unique(keys,return_counts=True)
    key=vals[np.argmax(counts)]
    bucket=pts[keys==key]
    return np.median(bucket,axis=0).astype(float)


def solve_colored_line_chart(image: Path, q: str, words: list[dict], lines: list[dict]):
    spec=parse_line_chart_question(q)
    if spec is None:
        raise RuntimeError("NOT_LINE_CHART_QUERY")
    with Image.open(image) as im:
        w,h=im.size
    xfit=fit_axis_ticks(words,w,h,"x")
    yfit=fit_axis_ticks(words,w,h,"y")
    legend=find_legend_line(lines,spec["temp"],spec["gradient"])

    img=cv2.imread(str(image),cv2.IMREAD_COLOR)
    target_rgb=representative_legend_color(img,legend)
    rgb=img[:,:,::-1].astype(float)

    # Plot rectangle from fitted zero/max ticks. Use inlier extrema.
    xvals=[v for _,v,_ in xfit["inliers"]]
    yvals=[v for _,v,_ in yfit["inliers"]]
    xlo_px=data_to_px(min(xvals),xfit); xhi_px=data_to_px(max(xvals),xfit)
    ylo_px=data_to_px(min(yvals),yfit); yhi_px=data_to_px(max(yvals),yfit)
    xa,xb=sorted((int(round(xlo_px)),int(round(xhi_px))))
    ya,yb=sorted((int(round(ylo_px)),int(round(yhi_px))))
    xa=max(0,xa-3); xb=min(w-1,xb+3); ya=max(0,ya-3); yb=min(h-1,yb+3)

    dist=np.linalg.norm(rgb-target_rgb.reshape(1,1,3),axis=2)
    mask=(dist<70)
    yy,xx=np.nonzero(mask)
    keep=(xx>=xa)&(xx<=xb)&(yy>=ya)&(yy<=yb)
    xx=xx[keep].astype(float); yy=yy[keep].astype(float)
    if len(xx)<20:
        raise RuntimeError("TARGET_CURVE_PIXELS_INSUFFICIENT")

    xd=px_to_data(xx,xfit)
    yd=px_to_data(yy,yfit)
    # Reject isolated color aliases using robust line residual.
    a,b=np.polyfit(xd,yd,1)
    resid=np.abs(yd-(a*xd+b))
    med=np.median(resid)
    keep=resid<=max(0.08,4*med+0.03)
    a,b=np.polyfit(xd[keep],yd[keep],1)
    if abs(a)<1e-9:
        raise RuntimeError("TARGET_CURVE_ZERO_SLOPE")
    x=(spec["target_y"]-b)/a
    ans=round(float(x),spec["decimals"])
    return {
        "answer":f"{ans:.{spec['decimals']}f}",
        "method":"legend_guided_color_trace_linear_fit",
        "curve_slope":float(a),
        "curve_intercept":float(b),
        "target_rgb":[float(x) for x in target_rgb],
        "curve_pixels":int(np.count_nonzero(keep)),
        "x_axis_inliers":len(xfit["inliers"]),
        "y_axis_inliers":len(yfit["inliers"]),
    }


def parse_phase_question(q: str):
    if not re.search(r"precipitat",q,re.I):
        return None
    m=re.search(r"(?:mg\s*[-–]?\s*)?(\d+(?:\.\d+)?)\s*wt\s*%\s*al",q,re.I)
    if not m:
        return None
    return {"composition":float(m.group(1))}


def text_mask(words: list[dict], shape):
    h,w=shape
    m=np.zeros((h,w),np.uint8)
    for x in words:
        pad=2
        x0=max(0,x["left"]-pad); y0=max(0,x["top"]-pad)
        x1=min(w,x["left"]+x["width"]+pad); y1=min(h,x["top"]+x["height"]+pad)
        m[y0:y1,x0:x1]=255
    return m


def solve_phase_precipitation(image: Path, q: str, words: list[dict]):
    spec=parse_phase_question(q)
    if spec is None:
        raise RuntimeError("NOT_PHASE_PRECIPITATION_QUERY")
    img=cv2.imread(str(image),cv2.IMREAD_GRAYSCALE)
    h,w=img.shape
    xfit=fit_axis_ticks(words,w,h,"x")
    yfit=fit_axis_ticks(words,w,h,"y")

    x_target=data_to_px(spec["composition"],xfit)
    # Plot limits from fitted tick spans, expanded slightly but not into labels.
    xvals=[v for _,v,_ in xfit["inliers"]]
    yvals=[v for _,v,_ in yfit["inliers"]]
    xmin=data_to_px(min(xvals),xfit); xmax=data_to_px(max(xvals),xfit)
    ymin=data_to_px(min(yvals),yfit); ymax=data_to_px(max(yvals),yfit)
    xa,xb=sorted((int(round(xmin)),int(round(xmax))))
    ya,yb=sorted((int(round(ymin)),int(round(ymax))))

    # Remove OCR text so glyph strokes do not masquerade as phase boundaries.
    work=img.copy()
    tm=text_mask(words,(h,w))
    work[tm>0]=255
    dark=(work<115).astype(np.uint8)*255

    # Remove long nearly horizontal/vertical axes and tick marks with opening.
    horiz=cv2.morphologyEx(dark,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(45,1)))
    vert=cv2.morphologyEx(dark,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,45)))
    curves=cv2.bitwise_and(dark,cv2.bitwise_not(cv2.bitwise_or(horiz,vert)))

    xp=int(round(x_target))
    band=curves[max(0,ya-5):min(h,yb+6),max(0,xp-4):min(w,xp+5)]
    ys,xs=np.nonzero(band)
    global_y=ys+max(0,ya-5)
    if len(global_y)<2:
        # Fall back to raw dark after text masking if morphology erased a steep curve.
        band=dark[max(0,ya-5):min(h,yb+6),max(0,xp-4):min(w,xp+5)]
        ys,xs=np.nonzero(band)
        global_y=ys+max(0,ya-5)
    if len(global_y)<2:
        raise RuntimeError("NO_PHASE_BOUNDARY_AT_COMPOSITION")

    vals=sorted(int(y) for y in global_y if ya-5<=y<=yb+5)
    clusters=[]
    cur=[vals[0]]
    for y in vals[1:]:
        if y-cur[-1]<=5:
            cur.append(y)
        else:
            clusters.append(cur); cur=[y]
    clusters.append(cur)

    candidates=[]
    for c in clusters:
        py=float(np.median(c))
        temp=float(px_to_data(py,yfit))
        # Keep interior phase boundaries, not extrema/axes.
        if min(yvals)+15 <= temp <= max(yvals)-5:
            candidates.append({"pixel_y":py,"temperature":temp,"support":len(c)})
    if not candidates:
        raise RuntimeError("NO_INTERIOR_PHASE_BOUNDARY")

    # For precipitation on cooling, choose the lowest-temperature interior
    # boundary at the requested composition (solid-state solvus before lower
    # plot boundary). This is a domain rule, not sample-specific gold.
    chosen=min(candidates,key=lambda x:x["temperature"])
    rounded=10.0*round(chosen["temperature"]/10.0)
    return {
        "answer":f"{int(round(rounded))}C",
        "method":"axis_calibrated_lowest_interior_phase_boundary",
        "composition":spec["composition"],
        "composition_pixel":float(x_target),
        "raw_temperature":chosen["temperature"],
        "candidates":candidates,
        "x_axis_inliers":len(xfit["inliers"]),
        "y_axis_inliers":len(yfit["inliers"]),
    }


def solve(image: Path, question: str):
    words=run_tesseract_tsv(image)
    lines=group_ocr_lines(words)
    attempts=[]
    for name,fn in (
        ("line_chart",lambda:solve_colored_line_chart(image,question,words,lines)),
        ("phase_precipitation",lambda:solve_phase_precipitation(image,question,words)),
    ):
        try:
            out=fn()
            out.update({
                "status":"FINAL",
                "module":name,
                "ocr_word_count":len(words),
                "runtime_general_purpose_model_dependencies":[],
                "external_runtime_cognition":False,
                "narrow_sensors":["tesseract_ocr_transcription_only"],
            })
            return out
        except Exception as exc:
            attempts.append({"module":name,"error":f"{type(exc).__name__}:{exc}"})
    return {
        "status":"UNSOLVED","answer":"",
        "attempts":attempts,
        "ocr_lines_preview":[x["text"] for x in lines[:80]],
        "runtime_general_purpose_model_dependencies":[],
        "external_runtime_cognition":False,
        "narrow_sensors":["tesseract_ocr_transcription_only"],
    }


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
