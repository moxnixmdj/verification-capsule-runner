#!/usr/bin/env python3
"""Fail if a workflow can directly start a protected Brain task outside the guard."""
import argparse,json,pathlib,re
DIRECT_PATTERNS=(
 r"python(?:3)?\s+run_[A-Za-z0-9_]*(?:parent|taska|taskb)[A-Za-z0-9_]*\.py",
 r"python(?:3)?\s+canonical/runtime/astra_runtime\.py\s+canonical/astra_runtime/missions/",
)
WRAPPER="execution_guard/github_actions_guarded_run_live.py"
def audit(root:pathlib.Path):
    wd=root/".github"/"workflows"; bypass=[]; guarded=[]
    if not wd.is_dir(): return {"status":"FAIL","reason":"WORKFLOW_DIR_MISSING","bypass":[],"guarded":[]}
    for p in sorted([*wd.glob("*.yml"),*wd.glob("*.yaml")]):
        t=p.read_text(encoding="utf-8",errors="replace"); rel=str(p.relative_to(root))
        direct=[x for x in DIRECT_PATTERNS if re.search(x,t)]
        if direct: bypass.append({"path":rel,"patterns":direct})
        if WRAPPER in t: guarded.append(rel)
    return {"schema":"BRAIN_EXECUTION_GUARD_LAUNCHER_AUDIT_V2","status":"PASS" if not bypass else "FAIL","wrapper":WRAPPER,"guarded":guarded,"bypass":bypass}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("root",nargs="?",default="."); a=ap.parse_args()
    r=audit(pathlib.Path(a.root).resolve()); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r["status"]=="PASS" else 1)
if __name__=="__main__": main()
