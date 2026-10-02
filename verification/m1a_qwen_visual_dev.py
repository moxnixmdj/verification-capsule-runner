import json, re
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from huggingface_hub import snapshot_download
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

DATA=json.loads(Path("m1a_visual_dev.json").read_text())
REPO="Qwen/Qwen3-VL-2B-Instruct"
REV="89644892e4d85e24eaac8bacfd4f463576704203"


def render(scene):
    w,h=scene["canvas"]
    image=Image.new("RGB",(w,h),"white")
    d=ImageDraw.Draw(image)
    for f in scene["features"]:
        kind=f["kind"]
        if kind=="circle":
            cx,cy=f["center"]; r=f["radius"]
            d.ellipse((cx-r,cy-r,cx+r,cy+r),outline="black",width=4)
            d.text((cx-r,cy+r+5),f["id"],fill="black")
        elif kind=="slot":
            cx,cy=f["center"]; length=f["length"]; width=f["width"]
            x1=cx-length/2; x2=cx+length/2; y1=cy-width/2; y2=cy+width/2
            r=width/2
            d.rectangle((x1+r,y1,x2-r,y2),outline="black",width=4)
            d.ellipse((x1,y1,x1+width,y2),outline="black",width=4)
            d.ellipse((x2-width,y1,x2,y2),outline="black",width=4)
            d.text((cx-10,y2+5),f["id"],fill="black")
    c=scene.get("callout")
    if c:
        ax,ay=(50,35)
        d.text((ax,ay),c["text"],fill="black")
        ex,ey=c["leader_endpoint"]
        d.line((ax+20,ay+15,ex,ey),fill="black",width=3)
    return image


def question(case):
    ids=[f["id"] for f in case["scene"]["features"]]
    if case["atom"]=="QUANTITY_TO_EQUIVALENT_FEATURE_SET":
        return (
            "This is a synthetic engineering drawing. Using only visible geometry and the callout, "
            "which labeled feature IDs does the quantity-bearing callout apply to? "
            "Return only a comma-separated sorted list of IDs, or AMBIGUOUS if the visible evidence does not uniquely determine the set."
        )
    if case["atom"]=="LEADER_TARGET_TO_COMPOUND_FEATURE":
        return (
            "Which labeled feature is uniquely targeted by the callout leader? "
            "Return only the feature ID, or AMBIGUOUS if not uniquely determined."
        )
    return (
        "Does the visible evidence uniquely determine which feature set this callout applies to? "
        "Return only RESOLVED or AMBIGUOUS."
    )


def expected_text(case):
    e=case["expected"]
    if e["status"]=="FAIL_CLOSED":
        return "AMBIGUOUS"
    if "feature_ids" in e:
        return ",".join(sorted(e["feature_ids"]))
    if "feature_id" in e:
        return e["feature_id"]
    return e["status"]


path=snapshot_download(
    repo_id=REPO,revision=REV,local_dir="/tmp/qwen3vl2b_m1a_dev",
    allow_patterns=["*.json","*.txt","*.safetensors","*.model"],
)
processor=AutoProcessor.from_pretrained(path,local_files_only=True)
model=Qwen3VLForConditionalGeneration.from_pretrained(
    path,local_files_only=True,dtype="auto",low_cpu_mem_usage=True,device_map={"":"cpu"}
)
model.eval()
rows=[]
for case in DATA["cases"]:
    image=render(case["scene"])
    messages=[{"role":"user","content":[
        {"type":"image","image":image},
        {"type":"text","text":question(case)},
    ]}]
    inputs=processor.apply_chat_template(
        messages,tokenize=True,add_generation_prompt=True,return_dict=True,return_tensors="pt"
    )
    with torch.inference_mode():
        out=model.generate(**inputs,max_new_tokens=12,do_sample=False)
    generated=out[0][inputs["input_ids"].shape[-1]:]
    answer=processor.decode(generated,skip_special_tokens=True,clean_up_tokenization_spaces=False).strip()
    expected=expected_text(case)
    norm=lambda s:re.sub(r"[^A-Z0-9,]","",s.upper())
    passed=norm(answer)==norm(expected)
    rows.append({
        "id":case["id"],"atom":case["atom"],"expected":expected,"answer":answer,"pass":passed
    })
result={
    "schema":"PROJECT_BRAIN_M1A_QWEN_VISUAL_DEV_RESULT_V1",
    "donor_repo":REPO,
    "donor_resolved_hf_sha":REV,
    "case_count":len(rows),
    "pass_count":sum(x["pass"] for x in rows),
    "accuracy":sum(x["pass"] for x in rows)/len(rows),
    "rows":rows,
    "classification":"DEV_SIGNAL_PRESENT" if sum(x["pass"] for x in rows)>=3 else "WEAK_OR_ABSENT",
    "heldout_cases_exposed":0,
    "capability_credit":False,
    "incremental_spend_usd":0,
}
print("RESULT_JSON="+json.dumps(result,sort_keys=True))
