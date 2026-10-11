#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, random, tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("solver",HERE/"solver_v1.py")
solver=importlib.util.module_from_spec(spec); spec.loader.exec_module(solver)

COLORS=["#7b1fa2","#009688","#e53935"]
STYLES=["-","--",":"]


def make_line_case(out:Path,rng:random.Random,i:int):
    temps=[600,800,1000]
    grads=[0.02,0.03,0.04]
    # Randomly shift the whole slope family while preserving three style-coded
    # temperature curves per color.
    base=rng.uniform(0.028,0.038)
    slopes={}
    fig,ax=plt.subplots(figsize=(rng.uniform(8.5,10.5),rng.uniform(4.8,6.2)),dpi=rng.choice([120,140,160]))
    x=np.linspace(0,100,500)
    for ti,temp in enumerate(temps):
        for gi,grad in enumerate(grads):
            slope=base+ti*rng.uniform(0.007,0.010)+(0.04-grad)*rng.uniform(0.18,0.26)
            slopes[(temp,grad)]=slope
            ax.plot(x,slope*x,color=COLORS[gi],linestyle=STYLES[ti],linewidth=rng.uniform(1.5,2.4),
                    label=f"{temp} degC / {grad:.2f} K/m")
    ymax=max(slopes.values())*100*1.12
    ax.set_xlim(0,100); ax.set_ylim(0,ymax)
    ax.set_xlabel("Time (Years)"); ax.set_ylabel("Vertical Deformation (Metres)")
    ax.legend(loc="center left",bbox_to_anchor=(1.02,0.5),fontsize=rng.choice([8,9,10]),frameon=True)
    fig.tight_layout()
    temp=rng.choice(temps); grad=rng.choice(grads)
    slope=slopes[(temp,grad)]
    x_true=rng.uniform(25,88); target_y=slope*x_true
    q=f"How long would it take an environment of {temp} degC / {grad:.2f} K/m to deform {target_y:.2f} metres vertically. Answer in years with 1 decimal place"
    p=out/f"line_{i:03d}.png"; fig.savefig(p); plt.close(fig)
    return {"kind":"line","image":str(p),"question":q,"truth":x_true,"tol":2.5}


def make_phase_case(out:Path,rng:random.Random,i:int):
    fig,ax=plt.subplots(figsize=(rng.uniform(7.2,9.0),rng.uniform(5.4,7.0)),dpi=rng.choice([120,140,160]))
    xmin,xmax=0,100; ymin=100
    eut_x=rng.uniform(12,22); eut_t=rng.uniform(410,470); top=rng.uniform(620,690)
    power=rng.uniform(0.75,1.35)
    xs=np.linspace(0,eut_x,300)
    solvus=ymin+(eut_t-ymin)*(xs/eut_x)**power
    liquidus=top-(top-eut_t)*(xs/eut_x)**rng.uniform(0.7,1.2)
    ax.plot(xs,solvus,color="black",linewidth=1.7)
    ax.plot(xs,liquidus,color="black",linewidth=1.7)
    # Right-side boundaries add realistic clutter but do not determine the query.
    xr=np.linspace(eut_x,100,350)
    ax.plot(xr,eut_t+(top-eut_t)*((xr-eut_x)/(100-eut_x))**1.1,color="black",linewidth=1.5)
    ax.axhline(eut_t,xmin=eut_x/100,xmax=0.84,color="black",linewidth=1.3)
    ax.set_xlim(xmin,xmax); ax.set_ylim(ymin,top+30)
    ax.set_xticks([0,20,40,60,80,100])
    yt=list(range(100,int(top//100)*100+1,100)); ax.set_yticks(yt)
    ax.set_xlabel("C$_{Al}$ (wt.%)"); ax.set_ylabel("T (°C)")
    ax.text(eut_x+8,eut_t-45,"Mg$_{17}$Al$_{12}$",fontsize=13)
    ax.text(5,eut_t+20,"(Mg)",fontsize=12)
    ax.text(45,top-80,"L",fontsize=14)
    fig.tight_layout()
    comp=rng.uniform(3,eut_x-2)
    truth=ymin+(eut_t-ymin)*(comp/eut_x)**power
    q=f"Using Mg-{comp:.1f} wt % Al alloy, at what temperature does Mg17Al12 precipitate? Round to the nearest 10 degrees."
    p=out/f"phase_{i:03d}.png"; fig.savefig(p); plt.close(fig)
    return {"kind":"phase","image":str(p),"question":q,"truth":10*round(truth/10),"tol":25.0}


def numeric_answer(s):
    import re
    m=re.search(r"[-+]?\d+(?:\.\d+)?",s or "")
    return float(m.group(0)) if m else None


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",required=True); ap.add_argument("--seed",type=int,default=20261011)
    ap.add_argument("--line-cases",type=int,default=20); ap.add_argument("--phase-cases",type=int,default=20)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(a.seed)
    cases=[]
    for i in range(a.line_cases): cases.append(make_line_case(out,rng,i))
    for i in range(a.phase_cases): cases.append(make_phase_case(out,rng,i))
    rows=[]
    for n,c in enumerate(cases):
        r=solver.solve(Path(c["image"]),c["question"])
        pred=numeric_answer(r.get("answer",""))
        ok=pred is not None and abs(pred-c["truth"])<=c["tol"]
        rows.append({
          "index":n,"kind":c["kind"],"question":c["question"],"truth":c["truth"],"tol":c["tol"],
          "answer":r.get("answer",""),"status":r.get("status"),"module":r.get("module"),
          "pass":ok,
        })
    by_kind={}
    for k in ("line","phase"):
        sub=[x for x in rows if x["kind"]==k]
        by_kind[k]={"passed":sum(x["pass"] for x in sub),"total":len(sub),
                    "accuracy":sum(x["pass"] for x in sub)/len(sub)}
    passed=sum(x["pass"] for x in rows); total=len(rows)
    result={
      "schema":"PROJECT_BRAIN_CHARTOGRAPHY_NATIVE_SYNTHETIC_GENERALIZATION_V1",
      "seed":a.seed,"passed":passed,"total":total,"accuracy":passed/total,"by_kind":by_kind,
      "pass":passed/total>=0.90 and all(v["accuracy"]>=0.85 for v in by_kind.values()),
      "runtime_general_purpose_model_dependencies":[],
      "external_runtime_cognition":False,
      "narrow_sensors":["tesseract_ocr_transcription_only"],
      "rows":rows,
    }
    (out/"synthetic_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result[k] for k in ("passed","total","accuracy","by_kind","pass")},sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__": main()
