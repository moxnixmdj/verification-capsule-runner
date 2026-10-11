from __future__ import annotations

import json
import time
from pathlib import Path

from canonical.runtime import osworld_v21_local_qwen_policy_v1 as policy
from canonical.runtime.osworld_v21_state_ops_v1 import normalize_state_ops


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


def normalized_state_ops(action: dict):
    if str(action.get("type") or "").upper() != "STATE_OPS":
        return None
    return normalize_state_ops(action.get("ops"))


def case_browser_observe() -> tuple[bool, dict]:
    state = base_state(
        "In the currently open browser, inspect the page and then fill the field "
        "labeled Name with Ada and submit the form. Do not guess the page state."
    )
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    op = action.get("op") if action.get("type") == "BROWSER_OP" else None
    passed = isinstance(op, dict) and str(op.get("type") or "").upper() == "OBSERVE"
    return passed, out


def case_file_write() -> tuple[bool, dict]:
    state = base_state(
        "Create /home/oai/share/note.txt containing exactly alpha followed by a newline. "
        "Use the most direct available state tool. Do not declare done until the file "
        "can be verified."
    )
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    ops = normalized_state_ops(action)
    matched = False
    if isinstance(ops, list):
        for op in ops:
            if (
                op.get("type") == "WRITE_TEXT"
                and op.get("path") == "/home/oai/share/note.txt"
                and op.get("text") == "alpha\n"
            ):
                matched = True
    return matched, out


def case_file_verify_after_write() -> tuple[bool, dict]:
    state = base_state(
        "Create /home/oai/share/note.txt containing exactly alpha followed by a newline."
    )
    state["screenshot_sha256"] = "2" * 64
    state["history"] = [{
        "actions": ["WAIT"],
        "response": "write file",
        "guest_result": {
            "type": "STATE_OPS",
            "ok": True,
            "status": "ok",
            "output": "",
        },
        "screenshot_sha256": "1" * 64,
    }]
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    ops = normalized_state_ops(action)
    matched = False
    if isinstance(ops, list):
        for op in ops:
            if (
                op.get("type") == "ASSERT_TEXT_EQUALS"
                and op.get("path") == "/home/oai/share/note.txt"
                and op.get("text") == "alpha\n"
            ):
                matched = True
    return matched, out


def case_document_convert() -> tuple[bool, dict]:
    state = base_state(
        "Convert /home/oai/share/input.md to PDF at /home/oai/share/output.pdf using a "
        "local document tool. Do not use GUI clicking if a direct application CLI is available. "
        "Verify that the output exists."
    )
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    ops = normalized_state_ops(action)
    cli_ok = False
    verify_ok = False
    if isinstance(ops, list):
        for op in ops:
            if op.get("type") == "RUN_CLI":
                argv = op.get("argv")
                if (
                    isinstance(argv, list)
                    and argv
                    and argv[0] in {"pandoc", "libreoffice", "soffice"}
                    and "/home/oai/share/input.md" in argv
                    and "/home/oai/share/output.pdf" in argv
                ):
                    cli_ok = True
            if (
                op.get("type") == "ASSERT_PATH_EXISTS"
                and op.get("path") == "/home/oai/share/output.pdf"
            ):
                verify_ok = True
    return cli_ok and verify_ok, out


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
    if action.get("type") != "BROWSER_OP" or not isinstance(action.get("op"), dict):
        return False, out
    op = action["op"]
    kind = str(op.get("type") or "").upper()
    repeated = kind == "CLICK_TEXT" and op.get("text") == "Save"
    target_ok = (
        (kind == "CLICK_TEXT" and op.get("text") == "Save changes")
        or (kind == "CLICK_ROLE" and op.get("name") == "Save changes")
    )
    return target_ok and not repeated, out


def case_browser_observe_after_mutation() -> tuple[bool, dict]:
    state = base_state(
        "In the current browser form, save the changes and finish only after checking "
        "the post-action page state."
    )
    state["screenshot_sha256"] = "2" * 64
    state["history"] = [{
        "actions": ["WAIT"],
        "response": "save changes",
        "browser_result": {
            "type": "CLICK_TEXT",
            "text": "Save changes",
            "url": "https://example.test/edit",
        },
        "screenshot_sha256": "1" * 64,
    }]
    out = policy.plan_state(state, timeout_s=300)
    action = one_action(out)
    op = action.get("op") if action.get("type") == "BROWSER_OP" else None
    passed = isinstance(op, dict) and str(op.get("type") or "").upper() == "OBSERVE"
    return passed, out


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
    return str(action.get("type") or "").upper() == "DONE", out


CASES = [
    ("browser_observe", case_browser_observe),
    ("file_write", case_file_write),
    ("file_verify_after_write", case_file_verify_after_write),
    ("document_convert", case_document_convert),
    ("browser_recovery", case_browser_recovery),
    ("browser_observe_after_mutation", case_browser_observe_after_mutation),
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
        "schema": "PROJECT_BRAIN_OSWORLD_V21_SYNTHETIC_POLICY_QUALIFICATION_V2",
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
    Path("out/osworld-v21-synthetic-policy-qualification-v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
