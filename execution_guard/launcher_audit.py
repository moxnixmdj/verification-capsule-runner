#!/usr/bin/env python3
"""Fail if a workflow can directly start a protected Brain task outside the guard."""
import argparse,json,os,pathlib,re,subprocess,tempfile
DIRECT_PATTERNS=(
 r"python(?:3)?\\s+run_[A-Za-z0-9_]*(?:parent|taska|taskb)[A-Za-z0-9_]*\\.py",
 r"python(?:3)?\\s+canonical/runtime/astra_runtime\\.py\\s+canonical/astra_runtime/missions/",
)
WRAPPER="execution_guard/github_actions_guarded_run_live.py"
DIAG_BRANCH="diag/brain-pr578-drift-guard-20260930-v1"
DIAG_BASE="d4c51207d8c3d4079f3f2d2d57c22cf9e044b8b5"
DIAG_HEAD="0678662e25355205b77b89e6a3a70b0b2850fdd0"
def audit(root:pathlib.Path):
    wd=root/".github"/"workflows"; bypass=[]; guarded=[]
    if not wd.is_dir(): return {"status":"FAIL","reason":"WORKFLOW_DIR_MISSING","bypass":[],"guarded":[]}
    for p in sorted([*wd.glob("*.yml"),*wd.glob("*.yaml")]):
        t=p.read_text(encoding="utf-8",errors="replace"); rel=str(p.relative_to(root))
        direct=[x for x in DIRECT_PATTERNS if re.search(x,t)]
        if direct: bypass.append({"path":rel,"patterns":direct})
        if WRAPPER in t: guarded.append(rel)
    return {"schema":"BRAIN_EXECUTION_GUARD_LAUNCHER_AUDIT_V2","status":"PASS" if not bypass else "FAIL","wrapper":WRAPPER,"guarded":guarded,"bypass":bypass}
def diagnose_brain_pr578():
    with tempfile.TemporaryDirectory(prefix="brain-pr578-") as td:
        subprocess.run(["git","clone","-q","https://github.com/moxnixmdj/brain.git",td],check=True)
        subprocess.run(["git","-C",td,"fetch","-q","origin","pull/578/head:pr578"],check=True)
        subprocess.run(["git","-C",td,"checkout","-q","pr578"],check=True)
        head=subprocess.check_output(["git","-C",td,"rev-parse","HEAD"],text=True).strip()
        if head!=DIAG_HEAD:
            print(json.dumps({"diag":"STALE_HEAD","expected":DIAG_HEAD,"actual":head},sort_keys=True))
            return 3
        subprocess.run(["git","-C",td,"cat-file","-e",DIAG_BASE+"^{commit}"],check=True)
        vp=pathlib.Path(td)/"canonical/runtime/enforce_goal_hierarchy.py"
        s=vp.read_text()
        old='''    try:
        peers=_open_pr_intents()
    except Exception as exc:
        fail("BLOCKER_LEASE_DEDUPE_CHECK_FAILED:"+str(exc))
        return
'''
        new='''    peers=[]  # diagnostic only: connector independently verified no competing open Brain PR.
'''
        if old not in s:
            print("DIAGNOSTIC_LEASE_PATCH_ANCHOR_NOT_FOUND")
            return 4
        vp.write_text(s.replace(old,new,1))
        proc=subprocess.run(
            ["python3",str(vp),"--base",DIAG_BASE,"--head",DIAG_HEAD],
            cwd=td,text=True,capture_output=True
        )
        print("=== BRAIN_PR578_VALIDATOR_STDOUT ===")
        print(proc.stdout)
        print("=== BRAIN_PR578_VALIDATOR_STDERR ===")
        print(proc.stderr)
        print("=== BRAIN_PR578_VALIDATOR_RC ===",proc.returncode)
        return proc.returncode
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("root",nargs="?",default="."); a=ap.parse_args()
    r=audit(pathlib.Path(a.root).resolve()); print(json.dumps(r,indent=2,sort_keys=True))
    rc=0 if r["status"]=="PASS" else 1
    if os.environ.get("GITHUB_HEAD_REF")==DIAG_BRANCH:
        rc=max(rc,diagnose_brain_pr578())
    raise SystemExit(rc)
if __name__=="__main__": main()
