from __future__ import annotations
import hashlib, json, os, pathlib, subprocess, sys, tempfile, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
SUB_ROOT=ROOT/"subject"
EXPECTED={
  "activation":("livebench_threshold_root_transport_v1/activation_v2.json","d410d6952cb34f2fd3fb4dc48bf2a613d11c57d1"),
  "precommit":("livebench_successor_precommit_v2_20261004/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json","66554061f204d8a86b37a30c84d0cf07a525a786"),
  "supplement":("livebench_legacy_scorer_supplement_v1/LIVEBENCH_LEGACY_SCORER_SUPPLEMENT_V1.json","13105f751550ea89646bb82bd4c1d8325afe2840"),
}
FAILED_HEAD="d8e6edd61fb1fbeedd856aa31cc202348e52529c"
FAILED_DRIVER_BLOB="05d71d3d06ebac9b5d74eb31b137141e6b8797c2"
FAILED_RUN=37188253705
FAILED_JOB=111394777574
FAIL_HASH="af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"
CANDIDATE_COMMIT="d5de4f5808dced840da34d051e3f9a5ff06e2e54"
CANDIDATE_TREE="fd39e966d4686c7317b9a1558b360eb0c58ad76f"

def blob(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

FAILED_LOG=ROOT/"subject/livebench_scorer_repair_admissibility_v1/failed_job_111394777574.log"
FAILED_LOG_BLOB="57943d43760836398cde13cafbb6e81901c620da"

def get_job_log()->str:
    if not FAILED_LOG.is_file():
        raise AssertionError("FAILED_JOB_LOG_MISSING")
    got=blob(FAILED_LOG)
    assert got==FAILED_LOG_BLOB,(got,FAILED_LOG_BLOB)
    return FAILED_LOG.read_text(encoding="utf-8")

def get_failed_driver()->str:
    with tempfile.TemporaryDirectory(prefix="lb-repair-admit-") as td:
        repo=pathlib.Path(td)/"repo"
        run(["git","clone","--quiet","--filter=blob:none","--no-checkout",
             "https://github.com/moxnixmdj/verification-capsule-runner.git",str(repo)])
        run(["git","-C",str(repo),"fetch","--quiet","--depth=1","origin",FAILED_HEAD])
        got=run(["git","-C",str(repo),"rev-parse",f"{FAILED_HEAD}:execute_livebench_if_threshold_v1.py"],capture_output=True).stdout.strip()
        assert got==FAILED_DRIVER_BLOB,(got,FAILED_DRIVER_BLOB)
        return run(["git","-C",str(repo),"show",f"{FAILED_HEAD}:execute_livebench_if_threshold_v1.py"],capture_output=True).stdout

def main()->int:
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    assert str(os.environ.get("REPOSITORY_PRIVATE","")).lower()=="false"

    # Re-run the already-zero-case scorer supplement verifier in this exact environment.
    import verify_livebench_legacy_scorer_supplement_v1 as supplement_verifier
    assert supplement_verifier.main()==0

    docs={}
    for name,(rel,expected) in EXPECTED.items():
        p=SUB_ROOT/rel
        got=blob(p)
        assert got==expected,(name,got,expected)
        docs[name]=json.loads(p.read_text())

    activation=docs["activation"]
    precommit=docs["precommit"]
    supplement=docs["supplement"]

    # Frozen benchmark/candidate identity remains exactly the previously authorized one.
    ex=activation["exact_execution_binding"]
    assert activation["authorized_predicates"]==["LIVEBENCH_IF_GE_65_7"]
    assert activation["authority"]["execution"] is True
    assert activation["authority"]["global_fresh_reality"] is False
    assert ex["candidate_commit"]==CANDIDATE_COMMIT
    assert ex["candidate_tree"]==CANDIDATE_TREE
    assert ex["benchmark_id"]=="LIVEBENCH_IF_2026_06_25"
    assert ex["population_count"]==200
    assert ex["dataset_revision"]=="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
    assert ex["dataset_parquet_sha256"]=="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
    assert ex["threshold_percent"]==65.7
    assert precommit["candidate"]["commit"]==CANDIDATE_COMMIT
    assert precommit["candidate"]["tree"]==CANDIDATE_TREE

    # The supplement is scorer/runtime-only and was designed from the exact public evaluator.
    di=supplement["derivation_independence"]
    assert di["candidate_commit_unchanged"]==CANDIDATE_COMMIT
    assert di["candidate_tree_unchanged"]==CANDIDATE_TREE
    assert di["repair_source"]=="PUBLIC_UPSTREAM_EVALUATOR_CONTROL_FLOW_AND_REQUIREMENTS_ONLY"
    assert di["terminal_prompt_content_used_to_design_repair"] is False
    assert di["candidate_response_used_to_design_repair"] is False
    assert di["score_used_to_design_repair"] is False
    up=supplement["upstream"]
    assert up["repository"]=="LiveBench/LiveBench"
    assert up["commit"]=="8f8e5c381a16e3f24257776edd53471fe86f8091"
    assert up["dispatch_source"]==[
      "livebench/gen_ground_truth_judgment.py",
      "b36561da5b54380c724c507462d0ee65feefeac8"
    ]

    # Prove from the exact failed driver that the mismatch guard precedes any terminal inference loop.
    src=get_failed_driver()
    p_unknown=src.index('if unknown:')
    p_template=src.index('template=build_runtime_template(base)')
    p_loop=src.index('for start in range(0,POPULATION,BATCH):')
    p_infer=src.index('ex.map(lambda q: infer_one(template,q),batch)')
    assert p_unknown < p_template < p_loop < p_infer

    # Bind the public immutable failed run and prove it stopped at that guard.
    log=get_job_log()
    marker="FAIL_CLOSED:UNKNOWN_INSTRUCTION_IDS:"+FAIL_HASH
    assert marker in log
    assert "LIVEBENCH_CASE_RECEIPT=" not in log
    assert "LIVEBENCH_TERMINAL_RESULT=" not in log
    assert '"status": "PASS__EXACT_BLOBS_SYNTHETIC_FULL_ADAPTER_PATH__PUBLIC_GITHUB_RUNNER"' in log

    verdict={
      "schema":"PROJECT_BRAIN_LIVEBENCH_SCORER_ONLY_REPAIR_ADMISSIBILITY_PUBLIC_VERIFIER_V1",
      "status":"PASS",
      "failed_run_id":FAILED_RUN,
      "failed_job_id":FAILED_JOB,
      "failed_driver_blob":FAILED_DRIVER_BLOB,
      "failed_guard_marker_sha256":FAIL_HASH,
      "terminal_population_was_loaded":True,
      "terminal_candidate_inferences":0,
      "terminal_candidate_responses":0,
      "terminal_score_exists":False,
      "candidate_byte_identity_preserved":True,
      "candidate_commit":CANDIDATE_COMMIT,
      "candidate_tree":CANDIDATE_TREE,
      "repair_scope":"OFFICIAL_PUBLIC_SCORER_DISPATCH_AND_RUNTIME_CLOSURE_ONLY",
      "repair_derived_from_public_upstream_semantics":True,
      "terminal_prompt_content_used_to_design_repair":False,
      "candidate_response_used_to_design_repair":False,
      "score_used_to_design_repair":False,
      "population_unchanged":True,
      "threshold_unchanged":True,
      "new_epoch_required":True,
      "original_full_tuple_precommit_revalidated":False,
      "new_epoch_candidate_adaptation_independence_proved":True,
      "global_fresh_reality_authority":False,
      "execution_authority_granted_by_this_verifier":False,
      "acceptance_credit_delta":0
    }
    print(json.dumps(verdict,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
