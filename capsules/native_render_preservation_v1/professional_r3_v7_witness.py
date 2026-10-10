from __future__ import annotations
import base64
from hashlib import sha1, sha256
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import tempfile

from canonical.runtime import native_artifact_cross_format_candidate_v1 as candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as structural
from canonical.runtime import native_artifact_render_preservation_proof_v1 as render
from canonical.runtime import professional_step_binding_authority_v1 as step_auth

SUBJECT_PATH=Path("canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json")
PROFILE_PATH=Path("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json")
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
PROFILE_BLOB="f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
SEED=73103
FMT="pdf"
EXPECTED_DEB={
    "libreoffice-core":"4:24.2.7-0ubuntu0.24.04.7",
    "poppler-utils":"24.02.0-1ubuntu9.10",
}
EXPECTED_PY={
    "python-docx":"1.2.0",
    "openpyxl":"3.1.5",
    "python-pptx":"1.0.2",
    "pypdf":"6.19.0",
    "Pillow":"12.3.0",
}

def git_blob(path:Path)->str:
    d=path.read_bytes()
    return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def h(data:bytes)->str:
    return sha256(data).hexdigest()

def canon(value)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

for pkg,expected in EXPECTED_DEB.items():
    got=subprocess.check_output(["dpkg-query","-W","-f=${Version}",pkg],text=True).strip()
    assert got==expected, (pkg,got,expected)
for pkg,expected in EXPECTED_PY.items():
    got=version(pkg)
    assert got==expected, (pkg,got,expected)

assert git_blob(SUBJECT_PATH)==SUBJECT_BLOB
assert git_blob(PROFILE_PATH)==PROFILE_BLOB
subject=json.loads(SUBJECT_PATH.read_text(encoding="utf-8"))
profile=json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
assert subject["subject_id"]==SUBJECT_ID
assert subject["subject_sha256"]==SUBJECT_SHA256
assert STEP_ID in profile["steps"]

case=structural.generate_case(FMT,SEED)
public=structural.public_task(case)
solved=candidate.solve(public)
assert solved.get("status")=="OK", solved
structural_verdict=structural.score_case(case,solved)
assert structural_verdict.get("pass") is True, structural_verdict
source=base64.b64decode(case["task"]["document_b64"],validate=True)
output=base64.b64decode(solved["output_b64"],validate=True)
visual_verdict=render.compare_renders(source,output,FMT)
assert visual_verdict.get("pass") is True, visual_verdict

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    spdf=render._to_pdf(source,FMT,root,"source")
    opdf=render._to_pdf(output,FMT,root,"output")
    spages=render._rasterize(spdf,root,"source_view")
    opages=render._rasterize(opdf,root,"output_view")
    assert len(spages)==len(opages)==1
    source_view=spages[0].read_bytes()
    output_view=opages[0].read_bytes()

source_sha=h(source)
output_sha=h(output)
source_view_sha=h(source_view)
output_view_sha=h(output_view)

goal="Apply exactly the declared bounded PDF text edit and preserve unrelated structure; render the exact audience view and bind observation channels."
decision_payload={
    "behavior_id":BEHAVIOR_ID,
    "claim_scope":"BOUNDED_R3_V7_REALIZATION_WITNESS",
    "format":FMT,
    "seed":SEED,
    "edit":case["task"]["edit"],
    "output_sha256":output_sha,
}
artifact_paths=[
    {"role":"source_artifact","sha256":source_sha},
    {"role":"output_artifact","sha256":output_sha},
]
hard_defect_profile_id="NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1"
detected_triggers=[]
run_context_sha256=step_auth.run_context_digest(
    goal=goal,
    decision_payload=decision_payload,
    artifact_paths=artifact_paths,
    hard_defect_profile_id=hard_defect_profile_id,
    detected_triggers=detected_triggers,
)

core={
    "schema":"PROJECT_BRAIN_PROFESSIONAL_R3_V7_REALIZATION_WITNESS_V1",
    "date":"2026-10-10",
    "subject_kind":"DECLARED_SYSTEM",
    "subject_id":SUBJECT_ID,
    "subject_sha256":SUBJECT_SHA256,
    "subject_git_blob_sha":SUBJECT_BLOB,
    "profile_git_blob_sha":PROFILE_BLOB,
    "behavior_id":BEHAVIOR_ID,
    "step_id":STEP_ID,
    "format":FMT,
    "seed":SEED,
    "goal":goal,
    "decision_payload":decision_payload,
    "artifact_paths":artifact_paths,
    "hard_defect_profile_id":hard_defect_profile_id,
    "detected_triggers":detected_triggers,
    "run_context_sha256":run_context_sha256,
    "source_artifact_sha256":source_sha,
    "output_artifact_sha256":output_sha,
    "source_audience_view_png_sha256":source_view_sha,
    "output_audience_view_png_sha256":output_view_sha,
    "source_artifact_b64":base64.b64encode(source).decode("ascii"),
    "output_artifact_b64":base64.b64encode(output).decode("ascii"),
    "source_audience_view_png_b64":base64.b64encode(source_view).decode("ascii"),
    "output_audience_view_png_b64":base64.b64encode(output_view).decode("ascii"),
    "structural_verdict":structural_verdict,
    "render_verdict":visual_verdict,
    "render_stack":{
        "libreoffice_core":EXPECTED_DEB["libreoffice-core"],
        "poppler_utils":EXPECTED_DEB["poppler-utils"],
        **EXPECTED_PY,
    },
    "scope":{
        "bounded_generated_explicit_low_level_text_edit_only":True,
        "arbitrary_semantic_target_correctness":False,
        "whole_contract_scope_equivalence":False,
        "global_r3_root_closure":False,
        "quality_authority":False,
        "terminal_authority":False,
    },
}
evidence_sha256=h(canon(core))
out={**core,"evidence_sha256":evidence_sha256}
print("R3_WITNESS_JSON="+json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False))
print("R3_WITNESS_EVIDENCE_SHA256="+evidence_sha256)
print("R3_WITNESS_RUN_CONTEXT_SHA256="+run_context_sha256)
