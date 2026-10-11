from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from canonical.runtime import osworld_v21_local_qwen_policy_v1 as policy


def base_state(instruction: str) -> dict:
    return {
        "instruction": instruction,
        "task_current_date": "2026-10-11",
        "screen": {"width": 1920, "height": 1080},
        "screenshot_sha256": "1" * 64,
        "ocr": {"text_items": []},
        "a11y_tree": None,
        "history": [],
    }


def one_action(out: dict) -> dict:
    actions = out.get("actions")
    assert isinstance(actions, list) and len(actions) == 1, out
    action = actions[0]
    assert isinstance(action, dict), out
    return action


def case_browser_observe() -> tuple[bool, dict]:
    state = base_state(
        "In the currently open browser, inspect the page and then fill the field "
        "labeled Name with Ada and submit the form. Do not guess the page state."
    )
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    op = action.get("op") if action.get("type") == "BROWSER_OP" else None
    passed = isinstance(op, dict) and op.get("type") == "OBSERVE"
    return passed, out


def case_file_write() -> tuple[bool, dict]:
    state = base_state(
        "Create /home/oai/share/note.txt containing exactly alpha followed by a newline. "
        "Use the most direct available state tool. Do not declare done until the file "
        "can be verified."
    )
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    ops = action.get("ops") if action.get("type") == "STATE_OPS" else None
    matched = False
    if isinstance(ops, list):
        for op in ops:
            if (
                isinstance(op, dict)
                and op.get("type") == "WRITE_TEXT"
                and op.get("path") == "/home/oai/share/note.txt"
                and op.get("text") == "alpha\n"
            ):
                matched = True
    return matched, out


def case_document_convert() -> tuple[bool, dict]:
    state = base_state(
        "Convert /home/oai/share/input.md to PDF at /home/oai/share/output.pdf using a "
        "local document tool. Do not use GUI clicking if a direct application CLI is available."
    )
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    ops = action.get("ops") if action.get("type") == "STATE_OPS" else None
    matched = False
    if isinstance(ops, list):
        for op in ops:
            if not isinstance(op, dict) or op.get("type") != "RUN_CLI":
                continue
            argv = op.get("argv")
            if (
                isinstance(argv, list)
                and argv
                and argv[0] in {"pandoc", "libreoffice", "soffice"}
                and "/home/oai/share/input.md" in argv
            ):
                matched = True
    return matched, out


def case_browser_recovery() -> tuple[bool, dict]:
    state = base_state(
        "In the current browser form, save the changes. Recover if the previous target "
        "was stale instead of repeating the identical failed action."
    )
    state["screenshot_sha256"] = "2" * 64
    state["history"] = [{
        "actions": ["WAIT"],
        "response": "click save",
        "operation_error": "BrowserOpsError:BROWSER_OP_FAILED:CLICK_TEXT:TimeoutError:stale target",
        "browser_result": {
            "type": "OBSERVE",
            "active_url": "https://example.test/edit",
            "active_title": "Edit",
            "visible_text": "Edit profile\nSave changes\nCancel",
            "controls": [
                {"tag": "button", "role": "button", "text": "Save changes", "aria_label": None},
                {"tag": "button", "role": "button", "text": "Cancel", "aria_label": None},
            ],
        },
        "screenshot_sha256": "1" * 64,
    }]
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    repeated = (
        action.get("type") == "BROWSER_OP"
        and isinstance(action.get("op"), dict)
        and action["op"].get("type") == "CLICK_TEXT"
        and action["op"].get("text") == "Save"
    )
    safe_progress = action.get("type") not in {"DONE", "FAIL"} and not repeated
    return safe_progress, out


def case_verified_finish() -> tuple[bool, dict]:
    state = base_state(
        "Create /home/oai/share/note.txt containing exactly alpha followed by a newline."
    )
    state["screenshot_sha256"] = "3" * 64
    state["history"] = [{
        "actions": ["WAIT"],
        "response": "verify file",
        "guest_result": {
            "type": "STATE_OPS",
            "ok": True,
            "status": "ok",
            "output": "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/note.txt\n",
        },
        "screenshot_sha256": "2" * 64,
    }]
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    passed = action.get("type") == "DONE"
    return passed, out


CASES = [
    ("browser_observe", case_browser_observe),
    ("file_write", case_file_write),
    ("document_convert", case_document_convert),
    ("browser_recovery", case_browser_recovery),
    ("verified_finish", case_verified_finish),
]


def main() -> int:
    rows = []
    started = time.time()
    for name, fn in CASES:
        row = {"name": name}
        try:
            passed, out = fn()
            row["pass"] = bool(passed)
            row["output"] = out
        except Exception as exc:
            row["pass"] = False
            row["error"] = type(exc).__name__ + ":" + str(exc)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)

    passed = sum(1 for r in rows if r["pass"])
    report = {
        "schema": "PROJECT_BRAIN_OSWORLD_V21_SYNTHETIC_POLICY_QUALIFICATION_V1",
        "status": "PASS" if passed == len(rows) else "FAIL",
        "passed": passed,
        "total": len(rows),
        "cases": rows,
        "elapsed_s": round(time.time() - started, 3),
        "terminal_osworld_cases_consumed": 0,
        "reference_trajectories_used_as_policy_input": False,
        "task_ids_used": False,
        "incremental_spend_usd": 0,
    }
    Path("out").mkdir(exist_ok=True)
    Path("out/osworld-v21-synthetic-policy-qualification-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
