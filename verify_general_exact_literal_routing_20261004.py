#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, sys, tempfile

SUBJECT=pathlib.Path("subject/general_exact_literal_routing_20261004/goal_compiler.py")
EXPECTED_BLOB="28dea3231fa429ee70b18071e45ba48b48a1ceb2"

def git_blob_sha(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load():
    spec=importlib.util.spec_from_file_location("verified_goal_compiler",SUBJECT)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def main():
    if git_blob_sha(SUBJECT)!=EXPECTED_BLOB:
        raise SystemExit("SUBJECT_BLOB_MISMATCH")
    src=SUBJECT.read_text(encoding="utf-8")
    if "SYNTHETIC_OK" in src:
        raise SystemExit("SPECIAL_CASE_TOKEN_PRESENT_IN_RUNTIME")
    m=load()
    root=pathlib.Path(tempfile.mkdtemp())

    positive=[
      ("Reply with exactly ROUTE_42.","ROUTE_42"),
      ("Respond with exactly NEUTRAL_TOKEN.","NEUTRAL_TOKEN"),
      ('Output exactly "hello neutral world".',"hello neutral world"),
      ("Return exactly 'quoted value'.","quoted value"),
      ("Print exactly `backtick value`.","backtick value"),
    ]
    for goal,expected in positive:
        out=m.compile_goal(goal,{},root)
        if out.get("compiler_mode")!="DETERMINISTIC_EXACT_LITERAL_RESPONSE":
            raise SystemExit("MODE_MISMATCH:"+goal)
        if out.get("finish_summary")!=expected:
            raise SystemExit("SUMMARY_MISMATCH:"+goal)
        if out.get("controller_actions")!=[{"type":"finish","args":{"summary":expected}}]:
            raise SystemExit("ACTION_MISMATCH:"+goal)
        if out.get("clause_coverage_verified") is not True:
            raise SystemExit("CLAUSE_COVERAGE_MISSING:"+goal)
        if "selected_capability" in out:
            raise SystemExit("CAPABILITY_ACQUISITION_LEAK:"+goal)

    negative=[
      "Reply with exactly hello neutral world.",
      "Explain exactly why the neutral example works.",
      "Reply with exactly TOKEN. Then explain it.",
      "Reply with exactly.",
      "Reply with exactly TOKEN\nThen continue.",
    ]
    for goal in negative:
        try:
            m.compile_goal(goal,{},root)
        except m.GoalCompilationFailure as e:
            if e.code!="GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH":
                raise SystemExit("WRONG_FAIL_CODE:"+goal+":"+e.code)
        else:
            raise SystemExit("AMBIGUOUS_INPUT_NOT_REJECTED:"+goal)

    direct=m._compile_exact_literal_response_goal("Reply with exactly ALPHA_9.")
    if direct.get("finish_summary")!="ALPHA_9":
        raise SystemExit("DIRECT_HELPER_GENERALIZATION_FAIL")

    print({
      "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__GENERAL_EXACT_LITERAL_ROUTING",
      "subject_git_blob_sha":EXPECTED_BLOB,
      "positive_cases":len(positive),
      "negative_cases":len(negative),
      "special_case_token_present":False,
      "capability_acquisition_required":False,
      "terminal_cases_consumed":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
    })
    return 0

if __name__=="__main__":
    raise SystemExit(main())
