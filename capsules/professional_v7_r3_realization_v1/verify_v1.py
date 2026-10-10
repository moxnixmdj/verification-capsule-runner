from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageChops

from canonical.runtime import native_artifact_cross_format_proof_v1 as structural
from canonical.runtime import native_artifact_render_preservation_proof_v1 as render
from capsules.professional_v7_r3_realization_v1 import professional_step_binding_authority_v1 as step_auth
from capsules.professional_v7_r3_realization_v1.produce_v1 import (
    BEHAVIOR_ID,
    EXPECTED_BLOBS,
    PRODUCER_ID,
    RUN_CONTEXT_BASIS,
    SCHEMA as EVIDENCE_SCHEMA,
    SEED,
    STEP_ID,
    SUBJECT_BLOB,
    SUBJECT_ID,
    SUBJECT_PATH,
    SUBJECT_SHA256,
)

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_V7_R3_REALIZATION_EVIDENCE_INDEPENDENT_VERIFY_V1"
VERIFIER_ID = "PUBLIC_PROFESSIONAL_V7_R3_INDEPENDENT_RENDER_VERIFIER_V1"


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


def rasterize(pdf: Path, root: Path, prefix: str) -> list[Path]:
    exe = shutil.which("pdftoppm")
    if not exe:
        raise RuntimeError("PDFTOPPM_MISSING")
    proc = subprocess.run(
        [exe, "-png", "-r", "96", str(pdf), str(root / prefix)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=90,
    )
    pages = sorted(root.glob(prefix + "-*.png"))
    if proc.returncode != 0 or not pages:
        raise RuntimeError("PDF_RASTER_FAILED:" + str(proc.returncode) + ":" + proc.stderr[-500:])
    return pages


def pixel_equal(a: Path, b: Path) -> bool:
    with Image.open(a) as ia, Image.open(b) as ib:
        if ia.size != ib.size:
            return False
        diff = ImageChops.difference(ia.convert("RGB"), ib.convert("RGB"))
        return diff.getbbox() is None


def fail(reason: str, **extra):
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "independent_verified": False,
        "semantic_preservation_verified": False,
        "evidence_scope_verified": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()
    input_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence_path = input_dir / "PROFESSIONAL_V7_R3_REALIZATION_EVIDENCE_V1.json"
    if not evidence_path.is_file():
        raise SystemExit(json.dumps(fail("EVIDENCE_MISSING")))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("schema") != EVIDENCE_SCHEMA or evidence.get("producer_id") != PRODUCER_ID:
        raise SystemExit(json.dumps(fail("EVIDENCE_IDENTITY_INVALID")))

    claimed_evidence_sha = evidence.get("evidence_sha256")
    base = dict(evidence)
    base.pop("evidence_sha256", None)
    recomputed_evidence_sha = hashlib.sha256(canon(base)).hexdigest()
    if claimed_evidence_sha != recomputed_evidence_sha:
        raise SystemExit(json.dumps(fail(
            "EVIDENCE_DIGEST_MISMATCH",
            claimed=claimed_evidence_sha,
            recomputed=recomputed_evidence_sha,
        )))

    subject = evidence.get("subject") or {}
    if subject != {
        "path": SUBJECT_PATH,
        "git_blob_sha": SUBJECT_BLOB,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA256,
    }:
        raise SystemExit(json.dumps(fail("V7_SUBJECT_TUPLE_MISMATCH")))

    if evidence.get("behavior_id") != BEHAVIOR_ID or evidence.get("step_id") != STEP_ID:
        raise SystemExit(json.dumps(fail("BEHAVIOR_OR_STEP_MISMATCH")))

    for rel, expected in EXPECTED_BLOBS.items():
        path = root / rel
        if not path.is_file() or path.is_symlink():
            raise SystemExit(json.dumps(fail("PINNED_RUNTIME_FILE_INVALID", path=rel)))
        actual = git_blob_sha(path)
        if actual != expected:
            raise SystemExit(json.dumps(fail(
                "PINNED_RUNTIME_BLOB_MISMATCH", path=rel, expected=expected, actual=actual
            )))

    expected_context = step_auth.run_context_digest(
        goal=RUN_CONTEXT_BASIS["goal"],
        decision_payload=RUN_CONTEXT_BASIS["decision_payload"],
        artifact_paths=RUN_CONTEXT_BASIS["artifact_paths"],
        hard_defect_profile_id=RUN_CONTEXT_BASIS["hard_defect_profile_id"],
        detected_triggers=RUN_CONTEXT_BASIS["detected_triggers"],
    )
    if evidence.get("run_context_basis") != RUN_CONTEXT_BASIS or evidence.get("run_context_sha256") != expected_context:
        raise SystemExit(json.dumps(fail("RUN_CONTEXT_BINDING_MISMATCH")))

    source_path = input_dir / "source.pdf"
    output_path = input_dir / "output.pdf"
    if not source_path.is_file() or not output_path.is_file():
        raise SystemExit(json.dumps(fail("ARTIFACT_BYTES_MISSING")))
    if sha256_file(source_path) != (evidence.get("source_artifact") or {}).get("sha256"):
        raise SystemExit(json.dumps(fail("SOURCE_ARTIFACT_HASH_MISMATCH")))
    if sha256_file(output_path) != (evidence.get("output_artifact") or {}).get("sha256"):
        raise SystemExit(json.dumps(fail("OUTPUT_ARTIFACT_HASH_MISMATCH")))

    case = structural.generate_case("pdf", SEED)
    reconstructed_source = base64.b64decode(case["task"]["document_b64"], validate=True)
    if reconstructed_source != source_path.read_bytes():
        raise SystemExit(json.dumps(fail("DETERMINISTIC_SOURCE_RECONSTRUCTION_MISMATCH")))

    candidate_view = {
        "status": "OK",
        "format": "pdf",
        "output_b64": base64.b64encode(output_path.read_bytes()).decode("ascii"),
        "terminal_authority": False,
    }
    structural_verdict = structural.score_case(case, candidate_view)
    if structural_verdict.get("pass") is not True:
        raise SystemExit(json.dumps(fail(
            "INDEPENDENT_STRUCTURAL_VERIFICATION_FAILED",
            structural_verdict=structural_verdict,
        )))

    visual = render.compare_renders(source_path.read_bytes(), output_path.read_bytes(), "pdf")
    if visual.get("pass") is not True:
        raise SystemExit(json.dumps(fail(
            "INDEPENDENT_RENDER_VERIFICATION_FAILED",
            render_verdict=visual,
        )))

    source_rows = evidence.get("source_audience_view")
    output_rows = evidence.get("output_audience_view")
    if not isinstance(source_rows, list) or not isinstance(output_rows, list) or not source_rows or len(source_rows) != len(output_rows):
        raise SystemExit(json.dumps(fail("AUDIENCE_VIEW_MANIFEST_INVALID")))

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        source_check = rasterize(source_path, td_path, "source_check")
        output_check = rasterize(output_path, td_path, "output_check")
        if len(source_check) != len(source_rows) or len(output_check) != len(output_rows):
            raise SystemExit(json.dumps(fail("AUDIENCE_VIEW_PAGE_COUNT_MISMATCH")))
        for rows, checks in ((source_rows, source_check), (output_rows, output_check)):
            for row, check in zip(rows, checks):
                stored = input_dir / str(row.get("file") or "")
                if not stored.is_file():
                    raise SystemExit(json.dumps(fail("AUDIENCE_VIEW_FILE_MISSING", file=row.get("file"))))
                if sha256_file(stored) != row.get("sha256"):
                    raise SystemExit(json.dumps(fail("AUDIENCE_VIEW_HASH_MISMATCH", file=row.get("file"))))
                if not pixel_equal(stored, check):
                    raise SystemExit(json.dumps(fail("AUDIENCE_VIEW_INDEPENDENT_RASTER_MISMATCH", file=row.get("file"))))

    result = {
        "schema": SCHEMA,
        "status": "PASS__EXACT_V7_SUBJECT_ARTIFACT_BYTES_AND_AUDIENCE_VIEW_INDEPENDENTLY_VERIFIED",
        "pass": True,
        "producer_id": PRODUCER_ID,
        "independent_verifier_id": VERIFIER_ID,
        "behavior_id": BEHAVIOR_ID,
        "step_id": STEP_ID,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA256,
        "subject_git_blob_sha": SUBJECT_BLOB,
        "run_context_sha256": expected_context,
        "evidence_sha256": claimed_evidence_sha,
        "source_artifact_sha256": sha256_file(source_path),
        "output_artifact_sha256": sha256_file(output_path),
        "audience_page_count": len(source_rows),
        "independent_verified": True,
        "semantic_preservation_verified": True,
        "evidence_scope_verified": True,
        "scope": "ONE_GENERATED_BOUNDED_EXPLICIT_LOW_LEVEL_PDF_TEXT_EDIT_UNDER_PINNED_NATIVE_RENDER_PRESERVATION_CONTRACT",
        "global_r3_root_closed": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    (out_dir / "PROFESSIONAL_V7_R3_REALIZATION_INDEPENDENT_VERIFY_V1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
