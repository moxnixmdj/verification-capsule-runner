#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import urllib.request
from pathlib import Path
from typing import Any

MODEL_BYTES = 93_511_232
MODEL_SHA256 = "61c69fc5ce91982e26c625d43be5c3c7f0f774da22f4fa4e45c37a80a22ddad4"
BUDGET_BYTES_EXCLUSIVE = 100_000_000

TASKS = [
    {
        "id": "plate_one_hole",
        "observations": "Front view: rectangle 80 mm wide and 50 mm high. Side view: constant depth 12 mm. A through hole diameter 10 mm is centered at x=40 mm, y=25 mm.",
        "expected": {"units":"mm","geometry":{"kind":"extruded","profile":"rectangle","width":80,"height":50,"thickness":12},"holes":[{"x":40,"y":25,"diameter":10,"hole_type":"through"}]},
    },
    {
        "id": "plate_two_holes",
        "observations": "Front view: rectangular plate 100 mm by 60 mm. Side view: thickness 8 mm. Two identical through holes diameter 6 mm lie on y=30 mm at x=20 mm and x=80 mm.",
        "expected": {"units":"mm","geometry":{"kind":"extruded","profile":"rectangle","width":100,"height":60,"thickness":8},"holes":[{"x":20,"y":30,"diameter":6,"hole_type":"through"},{"x":80,"y":30,"diameter":6,"hole_type":"through"}]},
    },
    {
        "id": "counterbore_plate",
        "observations": "Front view: rectangular plate 90 mm wide by 40 mm high. Thickness is 10 mm. At x=45 mm,y=20 mm there is a through bore diameter 8 mm with a counterbore diameter 16 mm and counterbore depth 3 mm.",
        "expected": {"units":"mm","geometry":{"kind":"extruded","profile":"rectangle","width":90,"height":40,"thickness":10},"holes":[{"x":45,"y":20,"diameter":8,"hole_type":"counterbore","counterbore_diameter":16,"counterbore_depth":3}]},
    },
    {
        "id": "stepped_shaft",
        "observations": "A rotationally symmetric stepped shaft is shown about the z axis. From z=0 to z=30 mm the outside diameter is 20 mm. From z=30 to z=50 mm the outside diameter is 30 mm. There is no bore.",
        "expected": {"units":"mm","geometry":{"kind":"revolved","segments":[{"z_start":0,"z_end":30,"outer_diameter":20,"inner_diameter":0},{"z_start":30,"z_end":50,"outer_diameter":30,"inner_diameter":0}]},"holes":[]},
    },
    {
        "id": "l_bracket",
        "observations": "An L bracket consists of two rectangular additive solids in one coordinate frame. Base: min corner (0,0,0), size dx=80,dy=40,dz=8. Vertical web: min corner (0,0,8), size dx=8,dy=40,dz=42. No holes or cuts.",
        "expected": {"units":"mm","geometry":{"kind":"multibody","bodies":[{"shape":"box","operation":"add","x":0,"y":0,"z":0,"dx":80,"dy":40,"dz":8},{"shape":"box","operation":"add","x":0,"y":0,"z":8,"dx":8,"dy":40,"dz":42}]},"holes":[]},
    },
    {
        "id": "triangular_prism",
        "observations": "A prism has a triangular XY profile with ordered vertices (0,0), (60,0), (0,40) mm and is extruded 12 mm along z. No holes.",
        "expected": {"units":"mm","geometry":{"kind":"extruded","profile":"polygon","profile_points":[[0,0],[60,0],[0,40]],"thickness":12},"holes":[]},
    },
    {
        "id": "unsupported_envelope",
        "observations": "The drawing shows a freeform cast surface that this schema cannot represent exactly. The readable overall envelope is width 120 mm, height 80 mm, depth 30 mm. Do not invent primitive geometry.",
        "expected": {"units":"mm","geometry":{"kind":"unsupported","envelope_width":120,"envelope_height":80,"envelope_depth":30},"holes":[]},
    },
    {
        "id": "inch_plate",
        "observations": "Units are inches. Rectangular plate width 4 in, height 2 in, thickness 0.25 in. One through hole diameter 0.5 in is centered at x=2 in,y=1 in.",
        "expected": {"units":"in","geometry":{"kind":"extruded","profile":"rectangle","width":4,"height":2,"thickness":0.25},"holes":[{"x":2,"y":1,"diameter":0.5,"hole_type":"through"}]},
    },
]

def call(endpoint: str, prompt: str, seed: int, max_tokens: int = 24) -> str:
    body = json.dumps({
        "model": "sub100mb-controller",
        "messages": [
            {"role":"system","content":"Answer the requested atomic field. Be literal and concise."},
            {"role":"user","content":prompt},
        ],
        "temperature": 0.0,
        "seed": seed,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()
    req = urllib.request.Request(endpoint.rstrip("/") + "/v1/chat/completions", data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

def parse_number(text: str) -> float | int | None:
    m = re.search(r"(?<![A-Za-z0-9_])-?(?:\d+(?:\.\d+)?|\.\d+)", text)
    if not m:
        return None
    v = float(m.group(0))
    return int(v) if v.is_integer() else v

def parse_choice(text: str, options: list[str]) -> str | None:
    low = text.lower()
    hits: list[tuple[int,str]] = []
    for option in options:
        m = re.search(r"(?<![a-z0-9_])" + re.escape(option.lower()) + r"(?![a-z0-9_])", low)
        if m:
            hits.append((m.start(), option))
    return min(hits)[1] if hits else None

class Micro:
    def __init__(self, endpoint: str, observations: str, task_index: int):
        self.endpoint=endpoint
        self.obs=observations
        self.task_index=task_index
        self.n=0
        self.trace=[]

    def _ask(self, question: str, kind: str, options: list[str] | None = None):
        self.n += 1
        prompt = (
            "Source observations:\n" + self.obs + "\n\n"
            + question + "\n"
            + ("Allowed answers: " + ", ".join(options) + ". " if options else "")
            + ("Answer with exactly one allowed word." if kind=="choice" else "Answer with one number only.")
        )
        raw=call(self.endpoint,prompt,seed=50_000+self.task_index*100+self.n)
        parsed=parse_choice(raw,options or []) if kind=="choice" else parse_number(raw)
        self.trace.append({"question":question,"kind":kind,"options":options,"raw":raw,"parsed":parsed})
        if parsed is None:
            # Non-oracular retry: same visible source, no hidden expected value.
            self.n += 1
            retry = (
                "Read the SAME source observations again:\n" + self.obs + "\n\n"
                + question + "\nYour previous answer could not be parsed. "
                + ("Return ONLY one of: " + " | ".join(options or []) if kind=="choice" else "Return ONLY the numeric value, with no units or prose.")
            )
            raw2=call(self.endpoint,retry,seed=60_000+self.task_index*100+self.n,max_tokens=12)
            parsed=parse_choice(raw2,options or []) if kind=="choice" else parse_number(raw2)
            self.trace.append({"question":question,"kind":kind,"options":options,"raw":raw2,"parsed":parsed,"retry":True})
        return parsed

    def choice(self,q,opts): return self._ask(q,"choice",opts)
    def num(self,q): return self._ask(q,"number")

def clamp_count(v: Any, max_n: int) -> int | None:
    if not isinstance(v,(int,float)) or isinstance(v,bool):
        return None
    i=int(v)
    return i if abs(float(v)-i) < 1e-9 and 0 <= i <= max_n else None

def build_partspec(endpoint: str, task: dict[str,Any], task_index: int) -> tuple[dict[str,Any] | None,list[dict[str,Any]],str | None]:
    m=Micro(endpoint,task["observations"],task_index)
    units=m.choice("What unit system is used?",["mm","in"])
    kind=m.choice("What is the primary geometry representation?",["extruded","revolved","multibody","unsupported"])
    if units is None or kind is None:
        return None,m.trace,"missing_units_or_geometry_kind"
    out: dict[str,Any]={"units":units,"geometry":{"kind":kind},"holes":[]}

    if kind=="extruded":
        profile=m.choice("What is the profile type?",["rectangle","polygon"])
        if profile is None: return None,m.trace,"missing_profile"
        g={"kind":"extruded","profile":profile}
        if profile=="rectangle":
            g["width"]=m.num("What is the rectangle width?")
            g["height"]=m.num("What is the rectangle height?")
            g["thickness"]=m.num("What is the extrusion thickness/depth?")
        else:
            g["thickness"]=m.num("What is the extrusion thickness/depth?")
            n=clamp_count(m.num("How many ordered profile vertices are explicitly given?"),8)
            if n is None: return None,m.trace,"invalid_profile_point_count"
            pts=[]
            for i in range(n):
                x=m.num(f"What is x coordinate of ordered profile vertex {i+1}?")
                y=m.num(f"What is y coordinate of ordered profile vertex {i+1}?")
                pts.append([x,y])
            g["profile_points"]=pts
        out["geometry"]=g

    elif kind=="revolved":
        n=clamp_count(m.num("How many constant-diameter axial segments are explicitly described?"),8)
        if n is None: return None,m.trace,"invalid_segment_count"
        segs=[]
        for i in range(n):
            segs.append({
                "z_start":m.num(f"For axial segment {i+1}, what is z_start?"),
                "z_end":m.num(f"For axial segment {i+1}, what is z_end?"),
                "outer_diameter":m.num(f"For axial segment {i+1}, what is the outside diameter?"),
                "inner_diameter":m.num(f"For axial segment {i+1}, what is the inside diameter? Use 0 when the source explicitly says no bore."),
            })
        out["geometry"]={"kind":"revolved","segments":segs}

    elif kind=="multibody":
        n=clamp_count(m.num("How many explicit rectangular solid bodies are described?"),8)
        if n is None: return None,m.trace,"invalid_body_count"
        bodies=[]
        for i in range(n):
            bodies.append({
                "shape":m.choice(f"For body {i+1}, what primitive shape is it?",["box"]),
                "operation":m.choice(f"For body {i+1}, what Boolean operation applies?",["add","cut"]),
                "x":m.num(f"For body {i+1}, what is the minimum-corner x?"),
                "y":m.num(f"For body {i+1}, what is the minimum-corner y?"),
                "z":m.num(f"For body {i+1}, what is the minimum-corner z?"),
                "dx":m.num(f"For body {i+1}, what is size dx?"),
                "dy":m.num(f"For body {i+1}, what is size dy?"),
                "dz":m.num(f"For body {i+1}, what is size dz?"),
            })
        out["geometry"]={"kind":"multibody","bodies":bodies}

    elif kind=="unsupported":
        out["geometry"]={
            "kind":"unsupported",
            "envelope_width":m.num("What is the readable overall envelope width?"),
            "envelope_height":m.num("What is the readable overall envelope height?"),
            "envelope_depth":m.num("What is the readable overall envelope depth?"),
        }

    # Hole extraction is separate from the main geometry.
    hcount=clamp_count(m.num("How many explicitly described holes or bores should appear in the holes list?"),6)
    if hcount is None: return None,m.trace,"invalid_hole_count"
    holes=[]
    for i in range(hcount):
        h={
            "x":m.num(f"For hole {i+1}, what is its center x coordinate?"),
            "y":m.num(f"For hole {i+1}, what is its center y coordinate?"),
            "diameter":m.num(f"For hole {i+1}, what is the through-bore diameter?"),
            "hole_type":m.choice(f"For hole {i+1}, what is its type?",["through","counterbore"]),
        }
        if h["hole_type"]=="counterbore":
            h["counterbore_diameter"]=m.num(f"For hole {i+1}, what is the counterbore diameter?")
            h["counterbore_depth"]=m.num(f"For hole {i+1}, what is the counterbore depth?")
        holes.append(h)
    out["holes"]=holes
    return out,m.trace,None

def same_number(a,b):
    return isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool) and abs(float(a)-float(b)) <= 1e-9

def validate(actual: Any, expected: Any, path="$") -> list[str]:
    if isinstance(expected,dict):
        if not isinstance(actual,dict): return [path+":expected_object"]
        errs=[]
        if set(actual)!=set(expected): errs.append(path+":keyset_mismatch")
        for k in expected:
            if k in actual: errs += validate(actual[k],expected[k],path+"."+k)
        return errs
    if isinstance(expected,list):
        if not isinstance(actual,list): return [path+":expected_list"]
        if len(actual)!=len(expected): return [path+":length_mismatch"]
        errs=[]
        for i,e in enumerate(expected): errs += validate(actual[i],e,f"{path}[{i}]")
        return errs
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        return [] if same_number(actual,expected) else [path+":value_mismatch"]
    return [] if actual==expected else [path+":value_mismatch"]

def wilson(s,n,z=1.959963984540054):
    if not n:return [0.0,1.0]
    p=s/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0,center-half),min(1,center+half)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--endpoint",default="http://127.0.0.1:8080")
    ap.add_argument("--out",default="sub100mb_typed_microquery_result_v2.json")
    args=ap.parse_args()

    records=[]
    total_queries=0
    for i,t in enumerate(TASKS):
        actual,trace,builder_error=build_partspec(args.endpoint,t,i)
        errors=["builder:"+builder_error] if builder_error else validate(actual,t["expected"])
        passed=not errors
        total_queries += len(trace)
        records.append({
            "task_id":t["id"],"passed":passed,"builder_error":builder_error,
            "errors":errors,"actual":actual,"trace":trace,
        })

    solved=sum(r["passed"] for r in records)
    result={
        "schema":"PROJECT_BRAIN_SUB100MB_TYPED_MICROQUERY_RESULT_V2",
        "status":"EMPIRICAL_RESEARCH_RESULT__ZERO_TERMINAL_CREDIT",
        "model":{
            "artifact":"SmolLM2-135M-Instruct-Q3_K_M.gguf",
            "sha256":MODEL_SHA256,
            "learned_bytes":MODEL_BYTES,
            "strict_budget_bytes_exclusive":BUDGET_BYTES_EXCLUSIVE,
            "remaining_bytes":BUDGET_BYTES_EXCLUSIVE-MODEL_BYTES,
        },
        "population":{"task_count":len(TASKS),"kind":"IDENTICAL_V1_SYNTHETIC_NONTERMINAL_PARTSPECLITE_TEXT_SURROGATES","terminal_cases_consumed":0},
        "summary":{
            "tasks_solved":solved,
            "task_success_rate":solved/len(TASKS),
            "task_success_wilson95":wilson(solved,len(TASKS)),
            "atomic_model_queries":total_queries,
            "mean_atomic_queries_per_task":total_queries/len(TASKS),
        },
        "records":records,
        "hard_nonclaims":[
            "NO_FRONTIER_CAPABILITY_CLAIM",
            "NO_IMAGE_PERCEPTION_CLAIM",
            "NO_TERMINAL_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
            "NO_OPEN_WORLD_GENERALIZATION_CLAIM",
            "HIDDEN_EXPECTED_OBJECT_USED_ONLY_AFTER_FINAL_ASSEMBLY_FOR_SCORING_NOT_FOR_BUILDER_FEEDBACK",
        ],
    }
    Path(args.out).write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result["summary"],indent=2))

if __name__=="__main__":
    main()
