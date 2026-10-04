#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
COMP=ROOT/"capsules/brain_compiler_public_ifeval/instruction_constraint_compiler_v1.py"
EXPECTED_COMP_BLOB="a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f"
GOOGLE_COMMIT="26d8ccdab6fec61b5c83ad6327ea8bda9e580288"
GOOGLE_BLOB="cbe52f6eecf3986fdac745b4acba4da1408eb146"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_FILES={
 "livebench/if_runner/instruction_following_eval/evaluation_main.py":"4a341984936c4d609644a3b77f8c030ac5aa7269",
 "livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
 "livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "livebench/if_runner/instruction_following_eval/instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
}

def blob_bytes(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main():
    assert blob_bytes(COMP.read_bytes())==EXPECTED_COMP_BLOB
    compiler=load_module(COMP,"brain_instruction_constraint_compiler_v1")

    raw=urllib.request.urlopen(
      f"https://raw.githubusercontent.com/google-research/google-research/{GOOGLE_COMMIT}/instruction_following_eval/data/input_data.jsonl",
      timeout=60).read()
    assert blob_bytes(raw)==GOOGLE_BLOB
    rows=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    assert len(rows)==541

    with tempfile.TemporaryDirectory(prefix="lb-legacy-frontier-") as td:
      lb=pathlib.Path(td)/"LiveBench"
      run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(lb)])
      run(["git","-C",str(lb),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT])
      run(["git","-C",str(lb),"checkout","--quiet","--detach",LIVEBENCH_COMMIT])
      for p,e in LEGACY_FILES.items():
        got=run(["git","-C",str(lb),"rev-parse",f"HEAD:{p}"],capture_output=True).stdout.strip()
        assert got==e,(p,got,e)
      sys.path.insert(0,str(lb/"livebench/if_runner"))
      from instruction_following_eval import instructions_registry

      emitted=full=0
      inst_total=inst_pass=0
      status_counts=collections.Counter()
      by_id=collections.defaultdict(lambda:collections.Counter(rows=0,emitted=0,checks=0,passed=0,full_rows=0))
      full_by_width=collections.Counter()
      total_by_width=collections.Counter()

      for row in rows:
        prompt=row["prompt"]
        out=compiler.synthesize_formal_only(prompt)
        status_counts[out["status"]]+=1
        response=out.get("response")
        total_by_width[len(row["instruction_id_list"])]+=1
        row_ok=True
        if response is None or not str(response).strip():
          row_ok=False
        else:
          emitted+=1
        local=[]
        for iid,kwargs in zip(row["instruction_id_list"],row["kwargs"]):
          by_id[iid]["rows"]+=1
          inst_total+=1
          ok=False
          if response is not None and str(response).strip():
            by_id[iid]["emitted"]+=1
            cls=instructions_registry.INSTRUCTION_DICT[iid]
            ins=cls(iid)
            clean={k:v for k,v in kwargs.items() if v is not None}
            ins.build_description(**clean)
            args=ins.get_instruction_args()
            if args and "prompt" in args:
              ins.build_description(prompt=prompt)
            try:
              ok=bool(ins.check_following(str(response)))
            except Exception:
              ok=False
          by_id[iid]["checks"]+=1
          by_id[iid]["passed"]+=int(ok)
          inst_pass+=int(ok)
          local.append(ok)
        row_ok = row_ok and all(local)
        if row_ok:
          full+=1
          full_by_width[len(row["instruction_id_list"])]+=1
          for iid in row["instruction_id_list"]:
            by_id[iid]["full_rows"]+=1

      receipt={
        "schema":"PROJECT_BRAIN_CURRENT_COMPILER_PUBLIC_LEGACY_IFEVAL_FRONTIER_V1",
        "status":"PASS_AUDIT_COMPLETED",
        "brain_compiler_git_blob_sha":EXPECTED_COMP_BLOB,
        "google_ifeval_commit":GOOGLE_COMMIT,
        "google_ifeval_git_blob_sha":GOOGLE_BLOB,
        "livebench_commit":LIVEBENCH_COMMIT,
        "public_rows":len(rows),
        "compiler_emitted_rows":emitted,
        "strict_full_pass_rows":full,
        "strict_full_pass_percent":100*full/len(rows),
        "instruction_checks":inst_total,
        "instruction_passes":inst_pass,
        "instruction_pass_percent":100*inst_pass/inst_total,
        "compiler_status_counts":dict(status_counts),
        "rows_by_instruction_count":dict(sorted(total_by_width.items())),
        "full_pass_rows_by_instruction_count":dict(sorted(full_by_width.items())),
        "per_instruction":{
          iid:dict(c) for iid,c in sorted(by_id.items(),key=lambda kv:(-kv[1]["rows"],kv[0]))
        },
        "terminal_livebench_rows_read":0,
        "terminal_prompt_or_kwargs_read":False,
        "model_inference_count":0,
        "acceptance_credit_delta":0,
      }
      pathlib.Path("brain_compiler_public_ifeval_frontier_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
      print(json.dumps(receipt,sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
