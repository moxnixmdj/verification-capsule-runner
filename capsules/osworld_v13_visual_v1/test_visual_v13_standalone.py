from __future__ import annotations
import hashlib, io
from PIL import Image, ImageDraw
from canonical.runtime.osworld_v21_visual_policy_overlay_v1 import route_visual
from canonical.runtime.osworld_v21_visual_region_grounding_v1 import ground_visual_region

RED=(220,45,45); WHITE=(255,255,255)

def image_bytes(circles=()):
    im=Image.new("RGB",(200,120),WHITE); d=ImageDraw.Draw(im)
    for box in circles: d.ellipse(box,fill=RED)
    out=io.BytesIO(); im.save(out,format="PNG"); return out.getvalue()

def state(instruction,img,history=None):
    return {"instruction":instruction,"history":list(history or []),"screenshot_bytes":img,
            "screenshot_sha256":hashlib.sha256(img).hexdigest()}

def action(out): return out["actions"][0]

def test_unique():
    img=image_bytes([(20,30,60,70)])
    out=ground_visual_region(img,color="red",shape="circle")
    assert out["pass"] is True and out["candidate_count"]==1
    assert 35<=out["click_point"]["x"]<=45

def test_ambiguous_fails_closed():
    img=image_bytes([(20,30,60,70),(140,30,180,70)])
    out=ground_visual_region(img,color="red",shape="circle")
    assert out["pass"] is False and out["reason"]=="AMBIGUOUS_MATCH"
    routed=route_visual(state("Click the red circle",img))
    assert routed["actions"]==[{"type":"WAIT"}]

def test_spatial_left():
    img=image_bytes([(20,30,60,70),(140,30,180,70)])
    out=route_visual(state("Click the red circle on the left",img))
    assert action(out)["type"]=="CLICK" and action(out)["x"]<100

def test_same_screen_no_repeat():
    img=image_bytes([(20,30,60,70)])
    first=route_visual(state("Click the red circle",img))
    row={"screenshot_sha256":hashlib.sha256(img).hexdigest(),"policy_receipt":first["_policy_receipt"]}
    second=route_visual(state("Click the red circle",img,[row]))
    assert second["actions"]==[{"type":"WAIT"}]
    assert second["_policy_receipt"]["route"]=="VISUAL_NO_PROGRESS_FAIL_CLOSED"

def test_changed_screen_completes_explicit_click():
    before=image_bytes([(20,30,60,70)]); after=image_bytes([])
    first=route_visual(state("Click the red circle",before))
    row={"screenshot_sha256":hashlib.sha256(before).hexdigest(),"policy_receipt":first["_policy_receipt"]}
    second=route_visual(state("Click the red circle",after,[row]))
    assert second["actions"]==[{"type":"DONE"}]
    assert second["_policy_receipt"]["route"]=="VISUAL_CLICK_TRANSITION_VERIFIED"
