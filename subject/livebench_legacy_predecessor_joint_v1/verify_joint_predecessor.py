#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
LIVEBENCH_ROOT = Path(os.environ["LIVEBENCH_ROOT"]).resolve()
sys.path.insert(0, str(LIVEBENCH_ROOT / "livebench" / "if_runner"))

from canonical.runtime.livebench_frozen_active_legacy15_v1 import ACTIVE_IDS  # noqa: E402
from canonical.runtime.livebench_legacy_visible_constraint_compiler_v4 import compile_visible_constraints  # noqa: E402
from canonical.runtime.livebench_legacy15_joint_witness_v1 import solve  # noqa: E402
from instruction_following_eval import instructions_registry  # noqa: E402

DATASET_REV = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
PARQUET_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
PARQUET_BYTES = 277319
EXPECTED_ROWS = 200
URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + DATASET_REV
    + "/data/test-00000-of-00001.parquet?download=true"
)
RECEIPT = HERE / "livebench_legacy_predecessor_joint_receipt_v1.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_kwargs(raw):
    out = {}
    for k, v in dict(raw or {}).items():
        if v is None:
            continue
        if hasattr(v, "tolist"):
            v = v.tolist()
        elif isinstance(v, tuple):
            v = list(v)
        out[str(k)] = v
    return out


def strict_score(response: str, ids: list[str], kwargs_list: list[dict]) -> tuple[bool, list[bool]]:
    flags = []
    for iid, raw_kw in zip(ids, kwargs_list):
        cls = instructions_registry.INSTRUCTION_DICT[iid]
        checker = cls(iid)
        checker.build_description(**clean_kwargs(raw_kw))
        flags.append(bool(response.strip()) and bool(checker.check_following(response)))
    return bool(flags) and all(flags), flags


def main() -> int:
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_PREDECESSOR_JOINT_RECEIPT_V1",
        "status": "FAIL_CLOSED",
        "bindings": {
            "dataset_revision": DATASET_REV,
            "dataset_sha256": PARQUET_SHA256,
            "dataset_bytes": PARQUET_BYTES,
            "expected_rows": EXPECTED_ROWS,
            "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
            "registry_blob": "903ed738398648c7cfac61d5ffa478c22f1f0891",
            "instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
            "instructions_util_blob": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
            "compiler_v4_blob": "f3d5165071438a7f0ce8cd57c0c3489aa3d08497",
            "joint_witness_blob": "30b13de760f8117ebe433fa3820d6dfdea46c05b",
            "active15_commitment": "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d",
        },
        "population": {},
        "replay": {},
        "diagnostics": {},
        "contamination_firewall": {
            "active_2024_11_25_terminal_rows_read": 0,
            "terminal_prompt_text_emitted": False,
            "predecessor_prompt_text_emitted": False,
            "response_text_emitted": False,
            "runtime_hidden_labels_used": False,
            "verifier_predecessor_labels_used": True,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "hard_nonclaims": [
            "PUBLIC_REMOVED_PREDECESSOR_REPLAY_ONLY",
            "PREDECESSOR_COVERAGE_IS_NOT_ACTIVE_TERMINAL_CASE_FREQUENCY",
            "NO_ACTIVE_2024_11_25_PROMPT_KWARG_RESPONSE_OR_SCORE_READ",
            "NO_LIVEBENCH_TERMINAL_PASS_OR_ACCEPTANCE_CREDIT",
            "NO_SEMANTIC_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "ACTIVE15_COMMITMENT_OPENING_REMAINS_A_SEPARATE_PROOF_OBLIGATION",
        ],
    }

    try:
        data_path = HERE / "predecessor.parquet"
        urllib.request.urlretrieve(URL, data_path)
        if data_path.stat().st_size != PARQUET_BYTES or sha256(data_path) != PARQUET_SHA256:
            raise RuntimeError("PINNED_PREDECESSOR_IDENTITY_MISMATCH")

        rows = pq.read_table(
            data_path,
            columns=["turns", "instruction_id_list", "kwargs", "livebench_release_date"],
        ).to_pylist()
        if len(rows) != EXPECTED_ROWS:
            raise RuntimeError(f"ROW_COUNT_MISMATCH:{len(rows)}")

        active = set(ACTIVE_IDS)
        compiler_pass = 0
        joint_candidate = 0
        strict_full_pass = 0
        active15_rows = 0
        active15_compiler_pass = 0
        active15_candidate = 0
        active15_strict_pass = 0
        route_counts = Counter()
        failure_reasons = Counter()
        failing_checker_ids = Counter()
        outside_active_ids = Counter()
        release_hist = Counter()

        for row in rows:
            turns = list(row.get("turns") or [])
            ids = [str(x) for x in (row.get("instruction_id_list") or [])]
            kwargs_list = list(row.get("kwargs") or [])
            if len(turns) != 1 or not isinstance(turns[0], str):
                raise RuntimeError("PREDECESSOR_TURN_SHAPE_DRIFT")
            if len(ids) != len(kwargs_list):
                raise RuntimeError("PREDECESSOR_LABEL_SHAPE_DRIFT")

            prompt = turns[0]
            is_active15 = set(ids) <= active
            if is_active15:
                active15_rows += 1
            else:
                for iid in sorted(set(ids) - active):
                    outside_active_ids[iid] += 1

            compiled = compile_visible_constraints(prompt)
            if compiled.get("status") == "PASS":
                compiler_pass += 1
                if is_active15:
                    active15_compiler_pass += 1

            out = solve(prompt)
            if out.get("status") != "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
                failure_reasons[str(out.get("error") or out.get("status") or "UNKNOWN")] += 1
                continue

            response = str(out.get("response") or "")
            joint_candidate += 1
            route_counts[str(out.get("route") or "UNKNOWN")] += 1
            if is_active15:
                active15_candidate += 1

            full, flags = strict_score(response, ids, kwargs_list)
            if full:
                strict_full_pass += 1
                if is_active15:
                    active15_strict_pass += 1
            else:
                for iid, ok in zip(ids, flags):
                    if not ok:
                        failing_checker_ids[iid] += 1

        receipt["population"] = {
            "rows": len(rows),
            "active15_only_rows": active15_rows,
            "outside_active15_rows": len(rows) - active15_rows,
            "release_histogram": dict(sorted(release_hist.items())),
        }
        receipt["replay"] = {
            "compiler_pass_rows": compiler_pass,
            "joint_candidate_rows": joint_candidate,
            "strict_full_pass_rows": strict_full_pass,
            "active15_compiler_pass_rows": active15_compiler_pass,
            "active15_joint_candidate_rows": active15_candidate,
            "active15_strict_full_pass_rows": active15_strict_pass,
            "active15_strict_full_pass_fraction": (
                active15_strict_pass / active15_rows if active15_rows else 0.0
            ),
            "route_counts": dict(sorted(route_counts.items())),
        }
        receipt["diagnostics"] = {
            "failure_reason_counts": dict(failure_reasons.most_common()),
            "failing_checker_id_counts": dict(failing_checker_ids.most_common()),
            "outside_active15_id_row_counts": dict(outside_active_ids.most_common()),
        }

        if active15_rows == 0:
            receipt["status"] = "FAIL_CLOSED__NO_ACTIVE15_PREDECESSOR_ROWS"
            code = 3
        elif active15_strict_pass == active15_rows:
            receipt["status"] = "PASS__ALL_ACTIVE15_PREDECESSOR_ROWS_FULL_SCORE"
            code = 0
        else:
            receipt["status"] = "MEASURED__PARTIAL_ACTIVE15_PREDECESSOR_COVERAGE"
            code = 2
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}:{exc}"
        code = 4
    finally:
        RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": receipt.get("status"),
            "population": receipt.get("population"),
            "replay": receipt.get("replay"),
            "error": receipt.get("error"),
        }, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
