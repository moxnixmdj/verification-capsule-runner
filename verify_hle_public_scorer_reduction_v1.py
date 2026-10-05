#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, subprocess, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"HLE_PUBLIC_SCORER_IMPLEMENTATION_REDUCTION_20261005_V1.json"
OUT=ROOT/"hle_public_scorer_reduction_receipt.json"
EXPECTED_CANDIDATE="ae770390fc51089b9fd7179d97a008db9e213441"
HLE_COMMIT="22ed3074b1e7b134bcbc09028d0ba320839b0655"
JUDGE_BLOB="4caca7c5e6eaa9c64ec33e5f1bcc93312e6c5b31"
README_BLOB="a948c9512541fff702aaf5e0c8bc371fded3689c"

def git_blob_bytes(b: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def main():
    raw=SUB.read_bytes()
    assert git_blob_bytes(raw)==EXPECTED_CANDIDATE
    c=json.loads(raw)
    assert c["target_predicate"]=="HLE_TOOLS_GE_67_7"
    assert c["execution_authority"] is False
    assert c["promotion_authority"] is False
    assert c["fresh_reality_authority"] is False
    assert c["accounting"]["acceptance_credit_delta"]==0
    assert c["accounting"]["terminal_cases_consumed"]==0
    assert "NO_CLAIM_THE_CAIS_DEFAULT_O3_MINI_JUDGE_IS_IDENTICAL_TO_ANTHROPIC_HLE_WITH_TOOLS_GRADING" in c["hard_nonclaims"]
    assert "ANTHROPIC_HLE_WITH_TOOLS_JUDGE_AND_CONTAMINATION_PROTOCOL_COMPARABILITY_OR_SEPARATELY_VERIFIED_CONSERVATIVE_STRONGER_SCORER_RELATION" in c["scheduler_delta"]["preserve"]

    with tempfile.TemporaryDirectory() as td:
        run("git","init","-q",td)
        run("git","remote","add","origin","https://github.com/centerforaisafety/hle.git",cwd=td)
        run("git","fetch","-q","--depth","1","origin",HLE_COMMIT,cwd=td)
        run("git","checkout","-q","--detach","FETCH_HEAD",cwd=td)
        head=run("git","rev-parse","HEAD",cwd=td)
        assert head==HLE_COMMIT
        judge=pathlib.Path(td,"hle_eval/run_judge_results.py")
        readme=pathlib.Path(td,"README.md")
        assert run("git","hash-object",str(judge),cwd=td)==JUDGE_BLOB
        assert run("git","hash-object",str(readme),cwd=td)==README_BLOB
        txt=judge.read_text(encoding="utf-8")
        assert 'JUDGE_PROMPT = """Judge whether the following [response]' in txt
        assert 'default="o3-mini-2025-01-31"' in txt
        assert '# prev: "gpt-4o-2024-08-06"' in txt
        assert 'correct: Literal["yes", "no"]' in txt
        assert 'accuracy = round(100 * sum(correct) / n, 2)' in txt
        assert '[correct_answer]: {correct_answer}' in txt
        assert "within a small margin of error for numerical problems" in txt

    receipt={
      "schema":"PROJECT_BRAIN_HLE_PUBLIC_SCORER_IMPLEMENTATION_REDUCTION_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__PINNED_PUBLIC_CAIS_SCORER_BYTES_AND_FAIL_CLOSED_REDUCTION_VERIFIED__ZERO_CREDIT",
      "verified":{
        "candidate_git_blob_sha":EXPECTED_CANDIDATE,
        "hle_commit":HLE_COMMIT,
        "judge_git_blob_sha":JUDGE_BLOB,
        "readme_git_blob_sha":README_BLOB,
        "official_judge_prompt_public":True,
        "official_default_judge":"o3-mini-2025-01-31",
        "accuracy_reducer_public":True,
        "anthropic_protocol_equivalence_claimed":False,
        "terminal_cases_consumed":0
      },
      "authority":{"execution":False,"promotion":False,"fresh_reality":False},
      "accounting":{"incremental_spend_usd":0,"acceptance_credit_delta":0}
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
