import json,time,re
from playwright.sync_api import sync_playwright

URL="https://arena.ai/text/direct"
TARGET="claude-sonnet-5-5-high"
PROMPT="Reply with exactly: ARENA_SONNET55_SUBSTRATE_OK"
out={"schema":"ARENA_SONNET55_SUBSTRATE_SMOKE_V1","terminal_proof_case_exposed":False,"target":TARGET,
     "selector_target_found":False,"selected_model":None,"prompt_submitted":False,"response_token_seen":False,"errors":[]}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={"width":1440,"height":1100})
    try:
        page.goto(URL,wait_until="domcontentloaded",timeout=90000)
        page.wait_for_timeout(7000)
        opened=False
        for pat in [re.compile(r"^Max$",re.I),re.compile(r"Select",re.I),re.compile(r"model",re.I)]:
            try:
                b=page.get_by_role("button",name=pat)
                if b.count():
                    b.first.click(timeout=5000); page.wait_for_timeout(1800); opened=True; break
            except Exception: pass
        inputs=page.locator("input")
        for i in range(inputs.count()):
            inp=inputs.nth(i)
            if inp.is_visible() and ("search" in (inp.get_attribute("placeholder") or "").lower()):
                inp.fill("sonnet"); page.wait_for_timeout(1600); break
        loc=page.get_by_text(TARGET,exact=True)
        if not loc.count():
            loc=page.get_by_text("claude-sonnet-5-5-high",exact=False)
        if loc.count():
            out["selector_target_found"]=True
            loc.first.click(timeout=7000); page.wait_for_timeout(1800)
            out["selected_model"]=TARGET
        if out["selected_model"]:
            editor=None
            for sel in ["textarea","[contenteditable='true']"]:
                q=page.locator(sel)
                vis=[q.nth(i) for i in range(q.count()) if q.nth(i).is_visible()]
                if vis: editor=vis[-1]; break
            if editor:
                editor.fill(PROMPT); editor.press("Enter"); out["prompt_submitted"]=True
                deadline=time.time()+90
                while time.time()<deadline:
                    page.wait_for_timeout(1500)
                    txt=page.locator("body").inner_text(timeout=10000)
                    if txt.count("ARENA_SONNET55_SUBSTRATE_OK")>=2:
                        out["response_token_seen"]=True; break
    except Exception as e:
        out["errors"].append(type(e).__name__+":"+str(e)[:800])
    finally:
        try: out["final_excerpt"]=page.locator("body").inner_text(timeout=5000)[-5000:]
        except Exception: pass
        browser.close()
out["status"]="PASS" if out["selected_model"] and out["prompt_submitted"] and out["response_token_seen"] else "FAIL_CLOSED"
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
