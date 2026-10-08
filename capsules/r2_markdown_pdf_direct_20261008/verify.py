from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types

HERE=Path(__file__).resolve().parent
MANIFEST=json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))

def git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

copies={
 "canonical/runtime/r2_markdown_pdf_direct_adequacy_v1.py": HERE/"r2_markdown_pdf_direct_adequacy_v1.py",
 "canonical/runtime/goal_compiler.py": HERE/"goal_compiler.py",
 "canonical/runtime/r2_direct_end_to_end_adequacy_v1.py": HERE/"r2_direct_end_to_end_adequacy_v1.py",
 "canonical/runtime/bound_capabilities/pandoc_weasyprint.py": HERE/"pandoc_weasyprint.py",
 "canonical/runtime/bound_capabilities/pdf_pypdf.py": HERE/"pdf_pypdf.py",
}
for private_path, local in copies.items():
    expected=MANIFEST["exact_git_blobs"][private_path]
    got=git_blob_sha(local)
    assert got==expected,(private_path,got,expected)
    compile(local.read_text(encoding="utf-8"),str(local),"exec")
    print("SOURCE_BINDING_PASS",private_path,got)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

producer=load("capsule_pandoc_weasyprint",HERE/"pandoc_weasyprint.py")
pdfmod=load("capsule_pdf_pypdf",HERE/"pdf_pypdf.py")

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
bound=types.ModuleType("canonical.runtime.bound_capabilities")
canonical.runtime=runtime
runtime.bound_capabilities=bound
bound.pdf_pypdf=pdfmod
canonical.__path__=[]
runtime.__path__=[]
bound.__path__=[]
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime
sys.modules["canonical.runtime.bound_capabilities"]=bound
sys.modules["canonical.runtime.bound_capabilities.pdf_pypdf"]=pdfmod

goal=types.ModuleType("canonical.runtime.goal_compiler")
live=types.ModuleType("canonical.runtime.live_integrated_brain_v1")
lossless=types.ModuleType("canonical.runtime.lossless_raw_task_contract_v1")
grounded=types.ModuleType("canonical.runtime.r2_grounded_candidate_policy_frontier_v1")
lossless.compile_contract=lambda *a,**k: None
grounded.goal_scoped_policy_id=lambda *a,**k: "unused"
runtime.goal_compiler=goal
runtime.live_integrated_brain_v1=live
sys.modules[goal.__name__]=goal
sys.modules[live.__name__]=live
sys.modules[lossless.__name__]=lossless
sys.modules[grounded.__name__]=grounded

route=load("capsule_route",HERE/"r2_markdown_pdf_direct_adequacy_v1.py")

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    (root/"canonical").mkdir()
    source=root/"canonical/source.md"
    output=root/"canonical/output.pdf"
    source_bytes=(
        b"# PROJECT BRAIN PDF\n\n"
        b"Alpha verify 7319.\n"
        b"Beta complete.\n"
    )
    source.write_bytes(source_bytes)
    source_sha=hashlib.sha256(source_bytes).hexdigest()
    visible=route._visible_text(source_bytes)
    assert visible=="PROJECT BRAIN PDF Alpha verify 7319. Beta complete.",visible

    produced=producer.run(
        {
            "markdown_path":"canonical/source.md",
            "output_path":"canonical/output.pdf",
            "timeout_s":120,
        },
        root,
    )
    assert produced["output_verified"] is True,produced
    assert output.read_bytes().startswith(b"%PDF-")
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha

    evidence=route._independent_verify(
        {
            "output_path":"canonical/output.pdf",
            "visible_text":visible,
            "visible_text_sha256":hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        },
        repo_root=root,
    )
    assert evidence["verified"] is True,evidence
    assert evidence["producer_independent_verifier"] is True,evidence
    assert evidence["verifier_capability_id"]=="pdf.extract.text.pypdf",evidence

    negative=route._independent_verify(
        {
            "output_path":"canonical/output.pdf",
            "visible_text":visible+" WRONG",
            "visible_text_sha256":hashlib.sha256((visible+" WRONG").encode("utf-8")).hexdigest(),
        },
        repo_root=root,
    )
    assert negative["verified"] is False,negative

print(json.dumps({
 "status":"PASS",
 "verified":[
   "exact_private_blob_binding",
   "real_pandoc_weasyprint_pdf_generation",
   "source_bytes_immutable",
   "producer_independent_pypdf_readback",
   "exact_route_visible_text_projection_matches",
   "semantic_mismatch_rejected"
 ]
},sort_keys=True))
