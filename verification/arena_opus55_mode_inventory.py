import json, re
from playwright.sync_api import sync_playwright

URL="https://arena.ai/text/direct"
TARGET_PATTERNS=[
    re.compile(r"claude[- ]opus[- ]5[.\- ]5", re.I),
    re.compile(r"opus[- ]5[.\- ]5", re.I),
]
MODES=["Direct","Side by Side","Agent Mode"]

def has_target(text):
    return any(p.search(text or "") for p in TARGET_PATTERNS)

out={
    "schema":"ARENA_OPUS55_MODE_INVENTORY_V1",
    "terminal_proof_case_exposed":False,
    "modes":{},
    "exact_opus55_route_found":False,
    "errors":[],
}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={"width":1440,"height":1100})
    page.goto(URL,wait_until="domcontentloaded",timeout=90000)
    page.wait_for_timeout(7000)

    for mode in MODES:
        rec={"tab_clicked":False,"selector_opened":False,"search_attempted":False,"target_visible":False,"excerpt":""}
        try:
            if mode!="Direct":
                tab=page.get_by_text(mode,exact=True)
                if tab.count():
                    tab.first.click(timeout=5000)
                    page.wait_for_timeout(3500)
                    rec["tab_clicked"]=True
            body=page.locator("body").inner_text(timeout=10000)
            if has_target(body):
                rec["target_visible"]=True
            # Try visible model/select buttons, then search inputs.
            opened=False
            for pat in [re.compile(r"Max",re.I),re.compile(r"Select",re.I),re.compile(r"model",re.I)]:
                try:
                    b=page.get_by_role("button",name=pat)
                    if b.count():
                        b.first.click(timeout=4000)
                        page.wait_for_timeout(1800)
                        opened=True
                        break
                except Exception:
                    pass
            rec["selector_opened"]=opened
            try:
                inputs=page.locator("input")
                for i in range(inputs.count()):
                    inp=inputs.nth(i)
                    if not inp.is_visible():
                        continue
                    ph=(inp.get_attribute("placeholder") or "").lower()
                    typ=(inp.get_attribute("type") or "").lower()
                    if "search" in ph or "model" in ph or typ=="search":
                        inp.fill("opus")
                        rec["search_attempted"]=True
                        page.wait_for_timeout(1800)
                        break
            except Exception as e:
                rec.setdefault("errors",[]).append("SEARCH:"+type(e).__name__+":"+str(e)[:300])
            body=page.locator("body").inner_text(timeout=10000)
            rec["target_visible"]=rec["target_visible"] or has_target(body)
            rec["excerpt"]=body[-12000:]
            if rec["target_visible"]:
                out["exact_opus55_route_found"]=True
        except Exception as e:
            rec.setdefault("errors",[]).append(type(e).__name__+":"+str(e)[:500])
        out["modes"][mode]=rec

    browser.close()

out["status"]="PASS_ROUTE_FOUND" if out["exact_opus55_route_found"] else "FAIL_CLOSED_NO_EXACT_OPUS55_ROUTE"
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
