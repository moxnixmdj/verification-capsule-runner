import json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL="https://arena.ai/text/direct"
TARGETS=["Claude Opus 5.5 (High)","claude-opus-5.5-high","Claude Opus 5.5"]
PROMPT="Reply with exactly: ARENA_OPUS55_SMOKE_OK"

out={
  "schema":"ARENA_OPUS55_DIRECT_GUEST_SMOKE_V1",
  "url":URL,
  "terminal_proof_case_exposed":False,
  "prompt":PROMPT,
  "selected_model":None,
  "selector_target_found":False,
  "prompt_submitted":False,
  "response_token_seen":False,
  "guest_blocker":None,
  "errors":[],
}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--disable-blink-features=AutomationControlled"])
    ctx=browser.new_context(
        viewport={"width":1440,"height":1100},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
    )
    page=ctx.new_page()
    try:
        page.goto(URL,wait_until="domcontentloaded",timeout=90000)
        page.wait_for_timeout(8000)
        body=page.locator("body").inner_text(timeout=10000)
        out["initial_body_excerpt"]=body[:6000]
        lower=body.lower()
        if any(x in lower for x in ["sign in","log in","captcha","verify you are human"]):
            out["guest_blocker"]="AUTH_OR_ANTIBOT_TEXT_VISIBLE_INITIAL"

        # Open likely model selector. Try buttons containing Max/Select first.
        opened=False
        for pat in [re.compile(r"^Max$",re.I),re.compile(r"Select",re.I),re.compile(r"model",re.I)]:
            try:
                loc=page.get_by_role("button",name=pat)
                if loc.count():
                    loc.first.click(timeout=5000)
                    page.wait_for_timeout(2500)
                    opened=True
                    break
            except Exception:
                pass
        if not opened:
            # Generic click on visible text Max, if it is not inside the prompt editor.
            try:
                loc=page.get_by_text("Max",exact=True)
                if loc.count():
                    loc.first.click(timeout=5000)
                    page.wait_for_timeout(2500)
                    opened=True
            except Exception:
                pass
        out["selector_open_attempted"]=opened
        after=page.locator("body").inner_text(timeout=10000)
        out["post_selector_body_excerpt"]=after[:10000]

        # Some selectors virtualize/filter the catalog. Search visible selector inputs for Opus.
        search_attempts=[]
        try:
            inputs=page.locator("input")
            for ii in range(inputs.count()):
                inp=inputs.nth(ii)
                if not inp.is_visible():
                    continue
                ph=inp.get_attribute("placeholder") or ""
                val=inp.get_attribute("value") or ""
                typ=inp.get_attribute("type") or ""
                search_attempts.append({"i":ii,"placeholder":ph,"value":val,"type":typ})
                if any(k in ph.lower() for k in ["search","model","filter"]) or typ in ("search","text",""):
                    try:
                        inp.fill("opus")
                        page.wait_for_timeout(1800)
                        filtered=page.locator("body").inner_text(timeout=10000)
                        if "opus" in filtered.lower():
                            out["post_search_body_excerpt"]=filtered[-12000:]
                            break
                    except Exception:
                        pass
        except Exception as e:
            out["errors"].append("SELECTOR_SEARCH:"+type(e).__name__+":"+str(e)[:500])
        out["visible_input_inventory"]=search_attempts[:20]

        target_locator=None
        for target in TARGETS:
            for exact in (True,False):
                try:
                    loc=page.get_by_text(target,exact=exact)
                    if loc.count():
                        target_locator=loc.first
                        out["selector_target_found"]=True
                        out["selector_target_text"]=target
                        break
                except Exception:
                    pass
            if target_locator:
                break

        if target_locator:
            try:
                target_locator.click(timeout=8000)
                page.wait_for_timeout(2500)
                out["selected_model"]=out.get("selector_target_text")
            except Exception as e:
                out["errors"].append("TARGET_CLICK:"+type(e).__name__+":"+str(e)[:500])

        selected_body=page.locator("body").inner_text(timeout=10000)
        out["selected_body_excerpt"]=selected_body[:10000]

        if out["selected_model"]:
            editor=None
            for sel in ["textarea","[contenteditable='true']","input[type='text']"]:
                try:
                    loc=page.locator(sel)
                    visible=[loc.nth(i) for i in range(loc.count()) if loc.nth(i).is_visible()]
                    if visible:
                        editor=visible[-1]
                        out["editor_selector"]=sel
                        break
                except Exception:
                    pass
            if editor is None:
                out["errors"].append("NO_VISIBLE_PROMPT_EDITOR")
            else:
                try:
                    if out["editor_selector"]=="[contenteditable='true']":
                        editor.click()
                        editor.fill(PROMPT)
                    else:
                        editor.fill(PROMPT)
                    editor.press("Enter")
                    out["prompt_submitted"]=True
                    deadline=time.time()+90
                    while time.time()<deadline:
                        page.wait_for_timeout(2000)
                        txt=page.locator("body").inner_text(timeout=10000)
                        if "ARENA_OPUS55_SMOKE_OK" in txt:
                            # Need at least two occurrences if editor still contains prompt.
                            out["response_token_occurrences"]=txt.count("ARENA_OPUS55_SMOKE_OK")
                            if out["response_token_occurrences"]>=2:
                                out["response_token_seen"]=True
                                break
                        low=txt.lower()
                        if "verify you are human" in low or "captcha" in low:
                            out["guest_blocker"]="ANTIBOT_AFTER_SUBMIT"
                            break
                    out["final_body_excerpt"]=page.locator("body").inner_text(timeout=10000)[-12000:]
                except Exception as e:
                    out["errors"].append("PROMPT_SUBMIT:"+type(e).__name__+":"+str(e)[:800])
    except Exception as e:
        out["errors"].append("TOPLEVEL:"+type(e).__name__+":"+str(e)[:1000])
    finally:
        try:
            Path("arena_smoke.png").write_bytes(page.screenshot(full_page=True))
        except Exception:
            pass
        browser.close()

out["status"]="PASS" if out["selected_model"] and out["prompt_submitted"] and out["response_token_seen"] else "FAIL_CLOSED"
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
