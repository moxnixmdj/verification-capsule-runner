#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, urllib.request
from pathlib import Path

LIVEBENCH_CSV = "https://livebench.ai/table_2026_06_25.csv"
HF_API = "https://huggingface.co/api/models/Qwen/Qwen3.8-27B"
EXPECTED_HF_SHA = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def find_row(rows, needles):
    needles=[n.lower() for n in needles]
    for row in rows:
        joined=" | ".join(row).lower()
        if all(n in joined for n in needles):
            return row
    raise AssertionError(f"row not found: {needles}")

def numeric_cells(row):
    out=[]
    for cell in row:
        s=cell.strip().replace("%","").replace("$","").replace(",","")
        try:
            out.append(float(s))
        except Exception:
            pass
    return out

def main() -> int:
    csv_raw=fetch(LIVEBENCH_CSV).decode("utf-8-sig")
    rows=list(csv.reader(io.StringIO(csv_raw)))
    assert rows, "empty livebench csv"
    header=rows[0]
    header_join=" | ".join(header).lower()
    assert "instruction" in header_join and "following" in header_join, header

    qwen=find_row(rows[1:], ["qwen3.8", "27b"])
    opus=find_row(rows[1:], ["claude", "5.5", "opus"])
    qnums=numeric_cells(qwen)
    onums=numeric_cells(opus)
    assert any(abs(x-72.7)<0.11 for x in qnums), qwen
    assert any(abs(x-65.7)<0.11 for x in onums), opus

    # Resolve the exact IF column instead of relying on its ordinal position.
    if_idx=None
    for i,h in enumerate(header):
        h2=h.lower().strip()
        if "instruction" in h2 and "following" in h2:
            if_idx=i
            break
    assert if_idx is not None
    q_if=float(qwen[if_idx].strip().replace("%",""))
    o_if=float(opus[if_idx].strip().replace("%",""))
    assert abs(q_if-72.7)<0.11, (q_if,qwen)
    assert abs(o_if-65.7)<0.11, (o_if,opus)
    assert q_if > o_if
    margin=q_if-o_if
    assert margin >= 6.9

    hf=json.loads(fetch(HF_API))
    assert hf["id"]=="Qwen/Qwen3.8-27B"
    assert hf["private"] is False
    assert hf["gated"] is False
    tags=set(hf.get("tags") or [])
    assert "license:apache-2.0" in tags, tags
    assert hf.get("sha")==EXPECTED_HF_SHA, hf.get("sha")

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_QWEN_OPEN_ROUTE_PUBLIC_VERIFICATION_V1",
      "status":"PASS",
      "livebench_release":"2026-06-25",
      "qwen3_8_27b_if_percent":q_if,
      "opus5_5_if_percent":o_if,
      "absolute_margin_percentage_points":margin,
      "qwen_repository":"Qwen/Qwen3.8-27B",
      "qwen_repository_private":False,
      "qwen_repository_gated":False,
      "qwen_license":"apache-2.0",
      "qwen_observed_sha":hf["sha"],
      "verified_deductions":[
        "A_PUBLIC_OPEN_WEIGHT_QWEN3_8_27B_ROUTE_EXISTS",
        "THE_OFFICIAL_LIVEBENCH_2026_06_25_IF_ROW_FOR_QWEN3_8_27B_EXCEEDS_THE_OPUS5_5_65_7_ROW",
        "THE_QWEN_WEIGHT_REPOSITORY_IS_PUBLIC_UNGATED_AND_APACHE_2_0_AT_THE_PINNED_OBSERVED_SHA"
      ],
      "hard_nonclaims":[
        "NO_BRAIN_INTERNALIZATION_OR_OWNERSHIP_CREDIT",
        "NO_RESOURCE_FIT_OR_RUNTIME_REPRODUCTION_CLAIM",
        "NO_SEMANTIC_CAPABILITY_CREDIT_FROM_LIVEBENCH_SCORE_ALONE",
        "NO_QUANTIZED_VARIANT_SCORE_TRANSFER"
      ],
      "accounting":{"terminal_cases_consumed":0,"acceptance_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
    }
    Path("livebench_qwen_open_route_public_verification_v1.json").write_text(
      json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
