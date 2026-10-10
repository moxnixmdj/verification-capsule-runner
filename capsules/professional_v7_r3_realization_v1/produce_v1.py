from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from canonical.runtime import native_artifact_cross_format_candidate_v1 as candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as structural
from capsules.native_render_preservation_v1.canonical.runtime import native_artifact_render_preservation_proof_v1 as render
from capsules.professional_v7_r3_realization_v1 import professional_step_binding_authority_v1 as step_auth

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_V7_R3_REALIZATION_EVIDENCE_V1"
PRODUCER_ID = "PUBLIC_PROFESSIONAL_V7_R3_ARTIFACT_PRODUCER_V1"
BEHAVIOR_ID = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
STEP_ID = "RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
SUBJECT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB = "1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID = "PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256 = "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
SEED = 7301

EXPECTED_BLOBS = {
    "canonical/runtime/native_artifact_cross_format_candidate_v1.py": "f3e5090647dd9029ab9f46efd06dc0c0d0addbc3",
    "canonical/runtime/native_artifact_cross_format_proof_v1.py": "904eb61171f5ee775ff7824c1be7778d7acc4a23",
    "capsules/native_render_preservation_v1/canonical/runtime/native_artifact_render_preservation_proof_v1.py": "39374e775d54cdc58315d7a1f877d834282a64f7",
    "canonical/runtime/ooxml_package_transaction.py": "970be62854c918b306ae3f62989009bfbd0e8fc7",
    "canonical/runtime/pdf_native_edit_transaction.py": "b9f673ffe0474d00a598089077ad93db40c00dd8",
    "capsules/professional_v7_r3_realization_v1/professional_step_binding_authority_v1.py": "27f3c137dae7f00925083a0824d008c2b4d10f0a",
}

RUN_CONTEXT_BASIS = {
    "goal": "Apply the declared bounded low-level PDF text edit and preserve the exact audience-visible layout outside the declared edit.",
    "decision_payload": {
        "context_id": "PROFESSIONAL_V7_R3_REALIZATION_SPECIMEN_V1",
        "format": "pdf",
        "seed": SEED,
        "operation": "PDF_REPLACE_UNIQUE_TEXT",
        "behavior_id": BEHAVIOR_ID,
    },
    "artifact_paths": ["source.pdf", "output.pdf"],
    "hard_defect_profile_id": "NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1",
    "detected_triggers": [],
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def rasterize(pdf: Path, out_dir: Path, prefix: str) -> list[dict]:
    exe = shutil.which("pdftoppm")
    if not exe:
        raise RuntimeError("PDFTOPPM_MISSING")
    raw_prefix = out_dir / prefix
    proc = subprocess.run(
        [exe, "-png", "-r", "96", str(pdf), str(raw_prefix)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=90,
    )
    pages = sorted(out_dir.glob(prefix + "-*.png"))
    if proc.returncode != 0 or not pages:
        raise RuntimeError("PDF_RASTER_FAILED:" + str(proc.returncode) + ":" + proc.stderr[-500:])
    from PIL import Image
    result = []
    for index, page in enumerate(pages, start=1):
        stable = out_dir / f"{prefix}_{index:03d}.png"
        page.replace(stable)
        with Image.open(stable) as im:
            dims = [int(im.size[0]), int(im.size[1])]
        result.append({
            "page_index": index - 1,
            "file": stable.name,
            "sha256": sha256_file(stable),
            "pixel_dimensions": dims,
            "bytes_b64": base64.b64encode(stable.read_bytes()).decode("ascii"),
        })
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for rel, expected in EXPECTED_BLOBS.items():
        path = root / rel
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("PINNED_RUNTIME_FILE_INVALID:" + rel)
        actual = git_blob_sha(path)
        if actual != expected:
            raise RuntimeError("PINNED_RUNTIME_BLOB_MISMATCH:" + rel + ":" + actual)

    case = structural.generate_case("pdf", SEED)
    public = structural.public_task(case)
    solved = candidate.solve(public)
    if solved.get("status") != "OK":
        raise RuntimeError("CANDIDATE_FAILED:" + json.dumps(solved, sort_keys=True))

    structural_verdict = structural.score_case(case, solved)
    if structural_verdict.get("pass") is not True:
        raise RuntimeError("STRUCTURAL_VERIFICATION_FAILED:" + json.dumps(structural_verdict, sort_keys=True))

    source = base64.b64decode(case["task"]["document_b64"], validate=True)
    output = base64.b64decode(solved["output_b64"], validate=True)
    source_path = out_dir / "source.pdf"
    output_path = out_dir / "output.pdf"
    source_path.write_bytes(source)
    output_path.write_bytes(output)

    visual = render.compare_renders(source, output, "pdf")
    if visual.get("pass") is not True:
        raise RuntimeError("RENDER_VERIFICATION_FAILED:" + json.dumps(visual, sort_keys=True))

    source_pages = rasterize(source_path, out_dir, "source_page")
    output_pages = rasterize(output_path, out_dir, "output_page")
    if len(source_pages) != len(output_pages):
        raise RuntimeError("AUDIENCE_PAGE_COUNT_MISMATCH")

    run_context_sha256 = step_auth.run_context_digest(
        goal=RUN_CONTEXT_BASIS["goal"],
        decision_payload=RUN_CONTEXT_BASIS["decision_payload"],
        artifact_paths=RUN_CONTEXT_BASIS["artifact_paths"],
        hard_defect_profile_id=RUN_CONTEXT_BASIS["hard_defect_profile_id"],
        detected_triggers=RUN_CONTEXT_BASIS["detected_triggers"],
    )

    evidence_basis = {
        "schema": SCHEMA,
        "status": "PASS__EXACT_V7_BOUND_PDF_REALIZATION_AND_AUDIENCE_VIEW_PRODUCED",
        "producer_id": PRODUCER_ID,
        "behavior_id": BEHAVIOR_ID,
        "step_id": STEP_ID,
        "subject": {
            "path": SUBJECT_PATH,
            "git_blob_sha": SUBJECT_BLOB,
            "subject_id": SUBJECT_ID,
            "subject_sha256": SUBJECT_SHA256,
        },
        "run_context_basis": RUN_CONTEXT_BASIS,
        "run_context_sha256": run_context_sha256,
        "case": {
            "format": "pdf",
            "seed": SEED,
            "edit": case["task"]["edit"],
            "request": case["task"]["request"],
        },
        "source_artifact": {
            "file": source_path.name,
            "sha256": sha256_file(source_path),
            "size_bytes": source_path.stat().st_size,
            "bytes_b64": base64.b64encode(source).decode("ascii"),
        },
        "output_artifact": {
            "file": output_path.name,
            "sha256": sha256_file(output_path),
            "size_bytes": output_path.stat().st_size,
            "bytes_b64": base64.b64encode(output).decode("ascii"),
        },
        "source_audience_view": source_pages,
        "output_audience_view": output_pages,
        "structural_verdict": structural_verdict,
        "render_verdict": visual,
        "runtime_git_blob_shas": EXPECTED_BLOBS,
        "carrier": {
            "repository": os.environ.get("GITHUB_REPOSITORY"),
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "workflow_sha": os.environ.get("GITHUB_SHA"),
            "head_ref": os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME"),
            "base_ref": os.environ.get("GITHUB_BASE_REF") or None,
        },
        "semantic_scope": "ONE_GENERATED_BOUNDED_EXPLICIT_LOW_LEVEL_PDF_TEXT_EDIT_UNDER_PINNED_NATIVE_RENDER_PRESERVATION_CONTRACT",
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    evidence_sha256 = hashlib.sha256(canon(evidence_basis)).hexdigest()
    evidence = {**evidence_basis, "evidence_sha256": evidence_sha256}
    (out_dir / "PROFESSIONAL_V7_R3_REALIZATION_EVIDENCE_V1.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "pass": True,
        "evidence_sha256": evidence_sha256,
        "run_context_sha256": run_context_sha256,
        "source_sha256": evidence["source_artifact"]["sha256"],
        "output_sha256": evidence["output_artifact"]["sha256"],
        "audience_pages": len(source_pages),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
