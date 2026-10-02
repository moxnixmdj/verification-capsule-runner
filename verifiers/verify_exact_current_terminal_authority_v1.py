from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT=Path("capsules/terminal_authority_exact_current_v1")
BRAIN=ROOT/"brain"

def git_blob(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+bytes([0])+data).hexdigest()

def run(cmd, **kwargs):
    p=subprocess.run(cmd,text=True,capture_output=True,**kwargs)
    if p.returncode!=0:
        raise AssertionError(f"command failed {cmd}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p

def main()->int:
    meta=json.loads((ROOT/"input.json").read_text(encoding="utf-8"))
    assert meta["schema"]=="PROJECT_BRAIN_EXACT_CURRENT_TERMINAL_AUTHORITY_CAPSULE_V1"
    assert meta["terminal_results_observed"]==0
    assert meta["fresh_terminal_evidence_consumed"]==0
    blobs=meta["source_git_blobs"]
    assert isinstance(blobs,dict) and len(blobs)>=20
    for rel,expected in sorted(blobs.items()):
        p=BRAIN/rel
        assert p.is_file(), rel
        actual=git_blob(p)
        assert actual==expected,(rel,expected,actual)

    env=dict(os.environ)
    env["PYTHONPATH"]=str(BRAIN)
    run([sys.executable,"-m","unittest","-v",
         "canonical.tests.test_terminal_wave_launch_authority_reducer_v1"],
        cwd=BRAIN,env=env)

    p=subprocess.run(
        [sys.executable,"canonical/runtime/terminal_wave_launch_authority_reducer_v1.py","."],
        cwd=BRAIN,env=env,text=True,capture_output=True
    )
    try:
        out=json.loads(p.stdout)
    except Exception as exc:
        raise AssertionError(f"reducer output not JSON rc={p.returncode}\n{p.stdout}\n{p.stderr}") from exc
    assert p.returncode==0,(out,p.stderr)
    assert out.get("pass") is True,out
    assert out.get("launch_authority") is True,out
    assert out.get("execution_authority") is True,out
    assert out.get("route_count")==12,out
    assert out.get("failed_predicates")==[],out
    assert out.get("terminal_results_observed",0)==0,out
    assert out.get("fresh_terminal_evidence_consumed",0)==0,out
    print("EXACT_CURRENT_TERMINAL_AUTHORITY_PASS",meta["brain_commit_sha"])
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
