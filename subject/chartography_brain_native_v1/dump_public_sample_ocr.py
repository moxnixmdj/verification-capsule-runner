from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"mirror"))

from canonical.runtime.bound_capabilities.image_ocr_tesseract_positioned import run as run_ocr

samples=[
    ROOT/"official"/"task_packs"/"sample_charts"/"charts"/"sample_chart_1.png",
    ROOT/"official"/"task_packs"/"sample_charts"/"charts"/"sample_chart_2.jpg",
]
outdir=ROOT/"out"/"ocr"
outdir.mkdir(parents=True,exist_ok=True)
for p in samples:
    obs=run_ocr({"path":str(p.relative_to(ROOT)),"language":"eng"},ROOT)
    slim={
        "source_path":obs["source_path"],
        "source_sha256":obs["source_sha256"],
        "selected_psm":obs["selected_psm"],
        "page_width":obs["page_width"],
        "page_height":obs["page_height"],
        "word_count":obs["word_count"],
        "line_count":obs["line_count"],
        "text":obs["text"],
        "text_items":obs["text_items"],
        "word_items":obs.get("word_items",[]),
        "terminal_semantic_authority":obs["terminal_semantic_authority"],
    }
    dest=outdir/(p.stem+".ocr.json")
    dest.write_text(json.dumps(slim,indent=2,sort_keys=True)+"\n")
    print("=== "+p.name+" ===")
    print(json.dumps(slim,sort_keys=True))
