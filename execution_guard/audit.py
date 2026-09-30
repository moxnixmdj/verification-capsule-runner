"""Fail-closed audit for scientific/one-shot workflow launch paths."""
from __future__ import annotations
import argparse,json,pathlib,re

GUARD_TOKEN="guard.py run"
DISCOVERY=re.compile(r"\b(?:python|python3|PYTHONPATH=\.\s+python)\s+[^\s]+\.py\b",re.I)
RISK_NAME=re.compile(r"(?:once|one.?shot)",re.I)
RISK_TEXT=re.compile(r"(?:ASTRA_DISABLE_MODEL_PLANNER|exactly once|execution_count)",re.I)

def norm(s): return " ".join(s.strip().split())
def audit(root:pathlib.Path,inventory_path:pathlib.Path)->list[str]:
    doc=json.loads(inventory_path.read_text())
    if doc.get("schema")!="BRAIN_EXECUTION_LAUNCHER_INVENTORY_V1": return ["INVENTORY_SCHEMA_INVALID"]
    entries=doc.get("launchers")
    if not isinstance(entries,list) or not entries:return ["INVENTORY_EMPTY"]
    expected={}; failures=[]; commands=set()
    for x in entries:
        try:
            wf=str(x["workflow"]); cmd=norm(str(x["science_command"])); binding=str(x["binding"])
        except Exception:
            failures.append("INVENTORY_ENTRY_INVALID"); continue
        expected.setdefault(wf,[]).append((cmd,binding)); commands.add(cmd)
        if not (root/binding).is_file(): failures.append(f"BINDING_FILE_MISSING:{binding}")
    wd=root/".github"/"workflows"
    if not wd.is_dir():return failures+["WORKFLOW_DIRECTORY_MISSING"]
    observed=set()
    for p in sorted([*wd.glob("*.yml"),*wd.glob("*.yaml")]):
        rel=p.relative_to(root).as_posix(); text=p.read_text()
        risky=bool(RISK_NAME.search(p.name) or RISK_TEXT.search(text))
        for n,raw in enumerate(text.splitlines(),1):
            line=norm(raw)
            for m in DISCOVERY.finditer(line):
                cmd=norm(m.group(0))
                if risky and not ("/test" in cmd or " test_" in cmd or "tests/" in cmd) and cmd not in commands:
                    failures.append(f"UNCLASSIFIED_EXECUTION:{rel}:{n}:{cmd}")
            for cmd,binding in expected.get(rel,[]):
                if cmd in line:
                    observed.add((rel,cmd))
                    if GUARD_TOKEN not in line:failures.append(f"UNGUARDED_EXECUTION:{rel}:{n}:{cmd}")
                    if "--binding "+binding not in line:failures.append(f"WRONG_OR_MISSING_BINDING:{rel}:{n}:{binding}")
        if rel in expected and "contents: write" not in text:failures.append(f"GUARD_STORE_WRITE_PERMISSION_MISSING:{rel}")
    for wf,xs in expected.items():
        if not (root/wf).is_file():failures.append(f"INVENTORIED_WORKFLOW_MISSING:{wf}");continue
        for cmd,_ in xs:
            if (wf,cmd) not in observed:failures.append(f"INVENTORIED_COMMAND_MISSING:{wf}:{cmd}")
    return sorted(set(failures))

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--inventory",required=True);a=p.parse_args()
    f=audit(pathlib.Path(a.root).resolve(),pathlib.Path(a.inventory).resolve())
    print(json.dumps({"status":"FAIL" if f else "PASS","violations":f},indent=2,sort_keys=True));return 1 if f else 0
if __name__=="__main__":raise SystemExit(main())
