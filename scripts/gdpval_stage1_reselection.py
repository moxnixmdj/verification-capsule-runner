#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from urllib.request import Request, urlopen

ROWS_API = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=openai%2Fgdpval&config=default&split=train"
)

ORIGINAL_EXCLUSIONS = {
    "83d10b06-26d1-4636-a32c-23f92c57f30b",
    "b57efde3-26d6-4742-bbff-2b63c43b4baa",
    "8a7b6fca-60cc-4ae3-b649-971753cbf8b9",
    "1752cb53-5983-46b6-92ee-58ac85a11283",
}

FROZEN_STAGE1 = {
    "XLSX": "a079d38f-c529-436a-beca-3e291f9e62a3",
    "PPTX": "be830ca0-b352-4658-a5bd-57139d6780ba",
    "TEXT_CONFIG": "2c249e0f-4a8c-4f8e-b4f4-6508ba29b34f",
}

NEWLY_EXPOSED = set(FROZEN_STAGE1.values())


def fetch_rows():
    rows = []
    for offset, length in ((0, 100), (100, 100), (200, 20)):
        url = f"{ROWS_API}&offset={offset}&length={length}"
        req = Request(url, headers={"User-Agent": "brain-public-verifier-stage1-reselection/1.0"})
        with urlopen(req, timeout=45) as r:
            payload = json.loads(r.read().decode("utf-8"))
        page = payload.get("rows")
        assert isinstance(page, list), f"missing rows at {offset}"
        rows.extend(page)
    assert len(rows) == 220, len(rows)
    return rows


def exts(files):
    return sorted({
        PurePosixPath(str(p)).suffix.lower()
        for p in (files or [])
        if PurePosixPath(str(p)).suffix
    })


def artifact_class(files):
    e = set(exts(files))
    # These rules are accepted only if they replay the already-frozen
    # September-30 selections exactly before applying the new exposures.
    if ".xlsx" in e:
        return "XLSX"
    if ".pptx" in e:
        return "PPTX"
    if ".txt" in e and (".yaml" in e or ".yml" in e):
        return "TEXT_CONFIG"
    return None


def candidates(rows, exclusions):
    out = {"XLSX": [], "PPTX": [], "TEXT_CONFIG": []}
    for item in rows:
        row = item.get("row") or {}
        tid = str(row.get("task_id") or "")
        if not tid or tid in exclusions:
            continue
        refs = list(row.get("reference_files") or [])
        dels = list(row.get("deliverable_files") or [])
        if len(refs) > 3 or not (1 <= len(dels) <= 2):
            continue
        cls = artifact_class(dels)
        if not cls:
            continue
        digest = hashlib.sha256(tid.encode()).hexdigest()
        out[cls].append({
            "task_id": tid,
            "task_id_sha256": digest,
            "sector": row.get("sector"),
            "occupation": row.get("occupation"),
            "reference_file_count": len(refs),
            "deliverable_file_count": len(dels),
            "extensions": exts(dels),
        })
    for cls in out:
        out[cls].sort(key=lambda x: (x["task_id_sha256"], x["task_id"]))
    return out


def pick(cands):
    return {cls: (rows[0] if rows else None) for cls, rows in cands.items()}


def main():
    rows = fetch_rows()

    replay_candidates = candidates(rows, ORIGINAL_EXCLUSIONS)
    replay = pick(replay_candidates)
    replay_ids = {k: (v or {}).get("task_id") for k, v in replay.items()}
    assert replay_ids == FROZEN_STAGE1, {
        "reason": "CLASSIFICATION_RULE_DOES_NOT_REPLAY_ORIGINAL_PRECOMMIT",
        "expected": FROZEN_STAGE1,
        "actual": replay_ids,
    }

    repaired_exclusions = ORIGINAL_EXCLUSIONS | NEWLY_EXPOSED
    repaired_candidates = candidates(rows, repaired_exclusions)
    replacements = pick(repaired_candidates)

    result = {
        "schema": "PROJECT_BRAIN_GDPVAL_STAGE1_CONTAMINATION_RESELECTION_VERIFICATION_V1",
        "status": "PASS__ORIGINAL_SELECTION_REPLAYED__REPLACEMENTS_COMPUTED_METADATA_ONLY",
        "population_count": 220,
        "selection_rule_replay": {
            "original_exclusion_count": len(ORIGINAL_EXCLUSIONS),
            "expected": FROZEN_STAGE1,
            "actual": replay_ids,
            "exact_match": True,
        },
        "contamination_repair": {
            "newly_exposed_task_ids": sorted(NEWLY_EXPOSED),
            "total_exclusion_count": len(repaired_exclusions),
            "replacement": replacements,
            "candidate_counts": {k: len(v) for k, v in repaired_candidates.items()},
            "class_exhausted": {
                k: len(v) == 0 for k, v in repaired_candidates.items()
            },
        },
        "privacy_and_contamination_boundary": {
            "fields_read_for_selection": [
                "task_id",
                "sector",
                "occupation",
                "reference_files",
                "deliverable_files",
            ],
            "prompt_used": False,
            "rubric_used": False,
            "gold_deliverable_content_used": False,
            "prior_model_submission_used": False,
        },
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
