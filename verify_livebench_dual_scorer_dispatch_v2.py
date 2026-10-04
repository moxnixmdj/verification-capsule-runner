#!/usr/bin/env python3
from __future__ import annotations
import hashlib, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
HELPER=ROOT/"livebench_dual_scorer_dispatch_v2.py"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
DISPATCH_SHA="b36561da5b54380c724c507462d0ee65feefeac8"
UTILS_SHA="8ce01747887ec0792c8f024e1972e34ece781676"

def run(cmd,**kw): return subprocess.run(cmd,check=True,text=True,**kw)
def main():
    from livebench_dual_scorer_dispatch_v2 import scorer_family,strip_think,modern_response,score_case
    assert scorer_family({"category":"instruction_following","livebench_release_date":"2025-11-24"})=="LEGACY_IFEVAL"
    assert scorer_family({"category":"instruction_following","livebench_release_date":"2025-11-25"})=="IFBENCH"
    assert strip_think("<think>private reasoning</think> answer")=="answer"
    assert modern_response("<think>x</think><solution> Hello World </solution>")=="Hello World"
    with tempfile.TemporaryDirectory(prefix="lb-dispatch-v2-") as td:
        repo=pathlib.Path(td)/"LiveBench"
        run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(repo)])
        run(["git","-C",str(repo),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT])
        run(["git","-C",str(repo),"checkout","--quiet","--detach",LIVEBENCH_COMMIT])
        got=run(["git","-C",str(repo),"rev-parse","HEAD:livebench/gen_ground_truth_judgment.py"],capture_output=True).stdout.strip()
        assert got==DISPATCH_SHA,(got,DISPATCH_SHA)
        got=run(["git","-C",str(repo),"rev-parse","HEAD:livebench/process_results/instruction_following/utils.py"],capture_output=True).stdout.strip()
        assert got==UTILS_SHA,(got,UTILS_SHA)
        source=(repo/"livebench/gen_ground_truth_judgment.py").read_text()
        assert 'm.question.get(\'category\') == \'instruction_following\' and m.question.get("livebench_release_date", "") < "2025-11-25"' in source
        assert 're.sub(f"<think>.*?<\\/think>", "", llm_answer, flags=re.DOTALL)' in source
        utils=(repo/"livebench/process_results/instruction_following/utils.py").read_text()
        assert "solution_match = re.search(r'<solution>(.*?)</solution>', llm_answer, re.DOTALL)" in utils

        sys.path.insert(0,str(repo/"livebench/if_runner"))
        from instruction_following_eval import evaluation_main as legacy_eval
        sys.path.insert(0,str(repo))
        from livebench.if_runner.ifbench import evaluation_lib as current_eval
        from livebench.process_results.instruction_following.utils import score_results

        oldq={"question_id":1,"category":"instruction_following","livebench_release_date":"2025-04-25",
              "instruction_id_list":["punctuation:no_comma"],"turns":["synthetic old"],"kwargs":[{}]}
        newq={"question_id":2,"category":"instruction_following","livebench_release_date":"2025-11-25",
              "instruction_id_list":["format:no_whitespace"],"turns":["synthetic new"],"kwargs":[{}]}
        old=score_case(oldq,"<think>ignored, with comma</think>Hello world",
                       legacy_eval=legacy_eval,current_eval=current_eval,score_results=score_results)
        new=score_case(newq,"<think>ignored text</think><solution>HelloWorld</solution>",
                       legacy_eval=legacy_eval,current_eval=current_eval,score_results=score_results)
        assert old["score"]==1.0 and old["scorer_family"]=="LEGACY_IFEVAL",old
        assert new["score"]==1.0 and new["scorer_family"]=="IFBENCH",new
        assert old["scoring_error"] is None and new["scoring_error"] is None
    print("PASS__LIVEBENCH_DUAL_SCORER_DISPATCH_V2__EXACT_RELEASE_BOUNDARY__THINK_AND_SOLUTION_PREPROCESSING__DUAL_SYNTHETIC_SCORE")
    return 0
if __name__=="__main__": raise SystemExit(main())
