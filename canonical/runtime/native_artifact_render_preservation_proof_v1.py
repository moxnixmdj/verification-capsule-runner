from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def _require(name: str) -> str:
    p = shutil.which(name)
    if not p:
        raise RuntimeError("MISSING_TOOL:" + name)
    return p


def _to_pdf(payload: bytes, fmt: str, root: Path, stem: str) -> Path:
    root = Path(root)
    if fmt == "pdf":
        out = root / (stem + ".pdf")
        out.write_bytes(payload)
        return out
    if fmt not in {"docx", "pptx", "xlsx"}:
        raise RuntimeError("FORMAT_UNSUPPORTED:" + fmt)
    libreoffice = _require("libreoffice")
    src = root / (stem + "." + fmt)
    src.write_bytes(payload)
    outdir = root / (stem + "_pdf")
    outdir.mkdir()
    profile = root / (stem + "_profile")
    proc = subprocess.run(
        [
            libreoffice,
            "--headless",
            "-env:UserInstallation=file://" + str(profile),
            "--convert-to", "pdf",
            "--outdir", str(outdir),
            str(src),
        ],
        text=True,
        capture_output=True,
        timeout=120,
    )
    out = outdir / (stem + ".pdf")
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        raise RuntimeError("LIBREOFFICE_RENDER_FAILED:" + str(proc.returncode) + ":" + (proc.stderr or proc.stdout)[-500:])
    return out


def _rasterize(pdf: Path, root: Path, stem: str) -> list[Path]:
    pdftoppm = _require("pdftoppm")
    prefix = Path(root) / stem
    proc = subprocess.run(
        [pdftoppm, "-png", "-r", "96", str(pdf), str(prefix)],
        text=True,
        capture_output=True,
        timeout=120,
    )
    pages = sorted(Path(root).glob(stem + "-*.png"))
    if proc.returncode != 0 or not pages:
        raise RuntimeError("PDF_RASTER_FAILED:" + str(proc.returncode) + ":" + proc.stderr[-500:])
    return pages
