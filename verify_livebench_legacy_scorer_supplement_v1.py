#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_legacy_scorer_supplement_v1/manifest.json"
EXPECTED_SUBJECT_BLOB="13105f751550ea89646bb82bd4c1d8325afe2840"
IFBENCH_FILES={
 "livebench/if_runner/ifbench/evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
 "livebench/if_runner/ifbench/instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
 "livebench/if_runner/ifbench/instructions_registry.py":"adfed4832877566e62970257b50c6fa32c302fb2",
 "livebench/if_runner/ifbench/instructions_util.py":"21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
}

def git_blob_bytes(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def run(cmd, **kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

def main():
    if sys.version_info[:2] != (3,12):
        raise SystemExit("FAIL:PYTHON_3_12_REQUIRED")
    raw=SUBJECT.read_bytes()
    if git_blob_bytes(raw)!=EXPECTED_SUBJECT_BLOB:
        raise SystemExit("FAIL:CANDIDATE_BYTES_DRIFT")
    m=json.loads(raw)
    if m.get("target_predicate")!="LIVEBENCH_IF_GE_65_7":
        raise SystemExit("FAIL:TARGET_DRIFT")
    if m["derivation_independence"].get("terminal_prompt_content_used_to_design_repair") is not False:
        raise SystemExit("FAIL:TERMINAL_PROMPT_CONTAMINATION")
    if m["derivation_independence"].get("candidate_response_used_to_design_repair") is not False:
        raise SystemExit("FAIL:CANDIDATE_RESPONSE_CONTAMINATION")
    if m["derivation_independence"].get("score_used_to_design_repair") is not False:
        raise SystemExit("FAIL:SCORE_CONTAMINATION")

    with tempfile.TemporaryDirectory(prefix="lb-legacy-scorer-") as td:
        repo=pathlib.Path(td)/"LiveBench"
        run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(repo)])
        commit=m["upstream"]["commit"]
        run(["git","-C",str(repo),"fetch","--quiet","--depth=1","origin",commit])
        run(["git","-C",str(repo),"checkout","--quiet","--detach",commit])
        head=run(["git","-C",str(repo),"rev-parse","HEAD"],capture_output=True).stdout.strip()
        if head!=commit:
            raise SystemExit("FAIL:UPSTREAM_COMMIT_DRIFT")

        expected=dict(m["upstream"]["legacy_files"])
        expected[m["upstream"]["dispatch_source"][0]]=m["upstream"]["dispatch_source"][1]
        expected.update(IFBENCH_FILES)
        observed={}
        for path,sha in expected.items():
            got=run(["git","-C",str(repo),"rev-parse",f"HEAD:{path}"],capture_output=True).stdout.strip()
            observed[path]=got
            if got!=sha:
                raise SystemExit(f"FAIL:UPSTREAM_BLOB_DRIFT:{path}:{got}:{sha}")

        dispatch=(repo/m["upstream"]["dispatch_source"][0]).read_text(encoding="utf-8")
        required=[
          "old_instruction_following_matches = [m for m in matches if m.question.get('category') == 'instruction_following'",
          'm.question.get("livebench_release_date", "") < "2025-11-25"',
          "instruction_following_process_results(if_questions, if_answers, task_name, model_id, debug)",
          "normal_matches = [m for m in matches if m not in agentic_coding_matches and m not in old_instruction_following_matches]",
        ]
        if not all(x in dispatch for x in required):
            raise SystemExit("FAIL:DISPATCH_RULE_NOT_EXACTLY_ESTABLISHED")

        sys.path.insert(0,str(repo))
        from livebench.if_runner.instruction_following_eval import evaluation_main as legacy
        from livebench.if_runner.ifbench import evaluation_lib as current

        legacy_prompt="Write a short sentence without commas."
        li=legacy.InputExample(
            key=1,
            instruction_id_list=["punctuation:no_comma"],
            prompt=legacy_prompt,
            kwargs=[{}],
        )
        lo=legacy.test_instruction_following_strict(li,{legacy_prompt:"Hello world"})
        if lo.follow_all_instructions is not True or lo.follow_instruction_list != [True]:
            raise SystemExit("FAIL:LEGACY_SYNTHETIC_SMOKE")

        ci=current.InputExample(
            key=2,
            instruction_id_list=["format:title_case"],
            prompt="Write two title-cased words.",
            kwargs=[{}],
        )
        co=current.test_instruction_following_strict(ci,"Hello World")
        if co.follow_all_instructions is not True or co.follow_instruction_list != [True]:
            raise SystemExit("FAIL:IFBENCH_SYNTHETIC_SMOKE")

        result={
          "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_PUBLIC_RUNNER_RESULT_V1",
          "pass":True,
          "status":"PASS__EXACT_UPSTREAM_LEGACY_PLUS_IFBENCH_DISPATCH__SYNTHETIC_DUAL_SCORER_SMOKE__ZERO_TERMINAL_CASES",
          "subject_git_blob_sha":EXPECTED_SUBJECT_BLOB,
          "upstream_commit":commit,
          "dispatch_cutoff":"2025-11-25",
          "legacy_path_for_release_before_cutoff":True,
          "ifbench_path_for_release_at_or_after_cutoff":True,
          "exact_upstream_blobs":observed,
          "legacy_synthetic_strict_pass":True,
          "ifbench_synthetic_strict_pass":True,
          "terminal_dataset_downloaded":False,
          "terminal_case_content_read":False,
          "brain_inferences":0,
          "candidate_bytes_changed":False,
          "incremental_spend_usd":0,
          "acceptance_credit_delta":0,
          "execution_authority":False,
          "promotion_authority":False,
          "fresh_reality_authority":False,
        }
        print("LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_RESULT="+json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
