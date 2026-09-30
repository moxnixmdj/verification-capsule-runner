#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, re

DEFAULT_PATTERNS=(
  r"python(?:3)?\s+run_[A-Za-z0-9_]*(?:parent|taska|taskb)[A-Za-z0-9_]*\.py",
  r"python(?:3)?\s+canonical/runtime/astra_runtime\.py\s+canonical/astra_runtime/missions/",
)
GUARD_MARKER="BRAIN_EXECUTION_GUARD_V1"

def audit(root:pathlib.Path)->dict:
    workflows=root/".github"/"workflows"; protected=[]; bypass=[]
    if not workflows.is_dir():
        return {"status":"FAIL","reason":"WORKFLOW_DIR_MISSING","protected":[],"bypass":[]}
    for path in sorted(list(workflows.glob("*.yml"))+list(workflows.glob("*.yaml"))):
        text=path.read_text(encoding="utf-8",errors="replace")
        if not any(re.search(p,text) for p in DEFAULT_PATTERNS): continue
        rel=str(path.relative_to(root)); protected.append(rel)
        if GUARD_MARKER not in text: bypass.append(rel)
    return {"status":"PASS" if not bypass else "FAIL","guard_marker":GUARD_MARKER,
            "protected":protected,"bypass":bypass}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("root",nargs="?",default=".")
    ns=ap.parse_args(); report=audit(pathlib.Path(ns.root).resolve())
    print(json.dumps(report,indent=2,sort_keys=True))
    raise SystemExit(0 if report["status"]=="PASS" else 1)
if __name__=="__main__": main()
