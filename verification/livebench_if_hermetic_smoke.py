#!/usr/bin/env python3
import hashlib, importlib, json, os, pathlib, re, shutil, subprocess, sys

ROOT=pathlib.Path("/tmp/livebench_src")
NLD=pathlib.Path("/tmp/nltk_data")
EXPECTED_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"

# Inputs are checked out by the workflow at exact frozen commits.
if not ROOT.exists():
    raise SystemExit("LIVEBENCH_SOURCE_MISSING")
if not NLD.exists():
    raise SystemExit("NLTK_DATA_MISSING")

# Work on a copy; upstream bytes remain untouched for hash verification.
work=pathlib.Path("/tmp/livebench_hermetic")
if work.exists():
    shutil.rmtree(work)
shutil.copytree(ROOT,work)
ins=work/"livebench/if_runner/ifbench/instructions.py"
util=work/"livebench/if_runner/ifbench/instructions_util.py"

s=ins.read_text()
# Delete proven dead spaCy bootstrap only.
s=s.replace("from spacy.cli import download\n","")
s=s.replace("import spacy\n","")
s=re.sub(
    r'if not spacy\.util\.is_package\("en_core_web_sm"\):\n\s*download\(\'en_core_web_sm\'\)\n',
    "",
    s,
)
if "spacy" in s.lower():
    raise RuntimeError("SPACY_REFERENCE_SURVIVED_PATCH")
ins.write_text(s)

u=util.read_text()
# With pinned stopwords already local, replace unconditional network download
# with a local existence check. Scoring behavior is unchanged.
u=u.replace("    nltk.download('stopwords')\n", '    nltk.data.find("corpora/stopwords")\n')
# Disable helper auto-download. It will see local punkt and do nothing; any
# missing resource must fail closed rather than touch network.
util.write_text(u)

# Hard network guard: any hidden runtime downloader must fail.
os.environ["NLTK_DATA"]=str(NLD)
import nltk
nltk.data.path.insert(0,str(NLD))
def blocked_download(*a,**k):
    raise RuntimeError("NETWORK_DOWNLOAD_FORBIDDEN")
nltk.download=blocked_download

sys.path.insert(0,str(work))
from livebench.if_runner.ifbench import instructions_registry

ids=sorted(instructions_registry.INSTRUCTION_DICT)
if len(ids)!=58:
    raise RuntimeError(f"CHECKER_COUNT_MISMATCH:{len(ids)}")

rows=[]
for iid in ids:
    cls=instructions_registry.INSTRUCTION_DICT[iid]
    obj=cls(iid)
    # Deterministic construction. Random-generated args are allowed here because
    # this is only import/call smoke, not boundary certification.
    import random
    random.seed("PROJECT_BRAIN_LIVEBENCH_HERMETIC_V1:"+iid)
    desc=obj.build_description()
    args=obj.get_instruction_args()
    keys=obj.get_instruction_args_keys()
    # Empty candidate call must not crash. Its truth value is not promoted as
    # boundary evidence because some checkers can vacuously accept emptiness.
    try:
        empty=bool(obj.check_following(""))
        call_ok=True
        err=None
    except Exception as e:
        empty=None
        call_ok=False
        err=type(e).__name__+":"+str(e)[:300]
    rows.append({
        "id":iid,
        "class":cls.__name__,
        "description_nonempty":bool(desc),
        "arg_keys":list(keys),
        "args_type":type(args).__name__,
        "empty_result":empty,
        "call_ok":call_ok,
        "error":err,
    })

bad=[x for x in rows if not x["call_ok"] or not x["description_nonempty"]]
out={
    "schema":"PROJECT_BRAIN_LIVEBENCH_IF_HERMETIC_RUNTIME_SMOKE_V1",
    "upstream_commit":EXPECTED_COMMIT,
    "checker_count":len(rows),
    "all_registered_checker_calls_completed":not bad,
    "failures":bad,
    "rows":rows,
    "network_downloads_allowed":False,
    "spacy_required":False,
    "terminal_case_content_read":False,
    "fresh_terminal_evidence_consumed":0,
    "incremental_spend_usd":0,
}
out["status"]="PASS" if not bad else "FAIL_CLOSED"
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
if bad:
    raise SystemExit(1)
