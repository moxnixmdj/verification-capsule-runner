from __future__ import annotations
import ast, hashlib, importlib.util, inspect, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
EXEC=ROOT/"subject/livebench_retry_epoch_v3_candidate/execute_livebench_if_threshold_v2_candidate.py"
EXEC_BLOB="09643b818a4d929b8907cd3222271abde804e9e3"
PUBLIC_ROOT=ROOT/"subject/root2_output_only_threshold_activation_v1_20261004/TERMINAL_ROOT_CAUSE_STATE_V1.json"
PUBLIC_ROOT_BLOB="601e82d00104b4ed36ee5968ad966a0c02e627c1"
ACT=ROOT/"subject/livebench_threshold_root_transport_v1/activation_v2.json"
ACT_BLOB="d410d6952cb34f2fd3fb4dc48bf2a613d11c57d1"

def blob(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load():
    spec=importlib.util.spec_from_file_location("lbexec",EXEC)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class Out:
    def __init__(self):
        self.follow_all_instructions=True
        self.follow_instruction_list=[True]

class LegacyFake:
    class InputExample:
        def __init__(self,**kw):
            self.__dict__.update(kw)
    expected=None
    @classmethod
    def test_instruction_following_strict(cls,inp,answers):
        assert isinstance(answers,dict)
        assert answers[inp.prompt]==cls.expected,(answers,cls.expected)
        return Out()

class ModernFake:
    class InputExample:
        def __init__(self,**kw):
            self.__dict__.update(kw)
    expected=None
    @classmethod
    def test_instruction_following_strict(cls,inp,answer):
        assert answer==cls.expected,(answer,cls.expected)
        return Out()

def main()->int:
    assert blob(EXEC)==EXEC_BLOB,(blob(EXEC),EXEC_BLOB)
    assert blob(PUBLIC_ROOT)==PUBLIC_ROOT_BLOB
    assert blob(ACT)==ACT_BLOB
    src=EXEC.read_text()
    ast.parse(src)

    mod=load()
    assert mod.BENCHMARK_ID=="LIVEBENCH_IF_2026_06_25"
    assert mod.POPULATION==200
    assert mod.THRESHOLD==0.657
    assert mod.THRESHOLD_MASS==131.4
    assert mod.DATASET_REV=="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
    assert mod.DATASET_SHA256=="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
    assert mod.DATASET_BYTES==537024
    assert mod.LIVEBENCH_COMMIT=="8f8e5c381a16e3f24257776edd53471fe86f8091"
    assert mod.BATCH==8
    assert mod.SCORER_SUPPLEMENT_BLOB=="13105f751550ea89646bb82bd4c1d8325afe2840"

    # Direct invocation must fail before any benchmark I/O.
    sig=inspect.signature(mod.main)
    assert sig.parameters["authorized"].default is False
    try:
        mod.main()
    except SystemExit as exc:
        assert str(exc)=="FAIL_CLOSED:VERIFIED_RETRY_EPOCH_LAUNCHER_REQUIRED"
    else:
        raise AssertionError("DIRECT_EXECUTION_DID_NOT_FAIL_CLOSED")

    required_scorer_blobs={
      "livebench/gen_ground_truth_judgment.py":"b36561da5b54380c724c507462d0ee65feefeac8",
      "livebench/if_runner/ifbench/evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
      "livebench/if_runner/ifbench/instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
      "livebench/if_runner/ifbench/instructions_registry.py":"adfed4832877566e62970257b50c6fa32c302fb2",
      "livebench/if_runner/ifbench/instructions_util.py":"21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
      "livebench/if_runner/instruction_following_eval/evaluation_main.py":"4a341984936c4d609644a3b77f8c030ac5aa7269",
      "livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
      "livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
      "livebench/if_runner/instruction_following_eval/instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
      "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
    }
    for p,h in required_scorer_blobs.items():
        assert mod.SCORER_FILES[p]==h

    # Exact branch-specific response preprocessing.
    oldq={"question_id":"old","livebench_release_date":"2025-05-30","turns":["p"],
          "instruction_id_list":["x"],"kwargs":[{"a":None,"b":"v"}]}
    LegacyFake.expected="legacy answer"
    score,allok,n,followed,err=mod.case_score(
        LegacyFake,ModernFake,oldq,"<think>hidden</think> legacy answer")
    assert (score,allok,n,followed,err)==(1.0,True,1,1,None)

    newq={"question_id":"new","livebench_release_date":"2025-11-25","turns":["p2"],
          "instruction_id_list":["y"],"kwargs":[{}]}
    ModernFake.expected="modern answer"
    score,allok,n,followed,err=mod.case_score(
        LegacyFake,ModernFake,newq,"junk <solution> modern answer </solution> tail")
    assert (score,allok,n,followed,err)==(1.0,True,1,1,None)

    # Structural invariants: official date split, per-family registry validation,
    # fixed order, no random selection, output-only threshold stopping, no raw response logging.
    required=[
      'release < "2025-11-25"',
      'legacy_registry.INSTRUCTION_DICT',
      'ifbench_registry.INSTRUCTION_DICT',
      'sel=sorted(sel,key=lambda q:str(q["question_id"]))',
      'case_order":"QUESTION_ID_ASCENDING_FIXED_PREEXECUTION"',
      '"adaptive_case_selection":False',
      '"case_replacement":False',
      'if lower >= THRESHOLD_MASS:',
      'if upper < THRESHOLD_MASS:',
      '"response_sha256":hashlib.sha256(answer.encode()).hexdigest()',
      'REPOSITORY_PRIVATE',
      'paid_external_model_or_api_used":False',
    ]
    for x in required:
        assert x in src,x
    forbidden=["random.shuffle","random.choice","secrets.choice","LIVEBENCH_TERMINAL_PROMPT=",
               '"response":answer','"prompt":q["turns"][0]']
    for x in forbidden:
        assert x not in src,x

    # Point-of-use readiness precedes dataset read.
    p_install=src.index("install_scorer_deps()")
    p_nltk=src.index("prepare_nltk(base)")
    p_clone=src.index("lb=clone_livebench(base)")
    p_dataset=src.index("parquet=download_dataset(base)")
    assert p_install < p_nltk < p_clone < p_dataset

    act=json.loads(ACT.read_text())
    assert act["authorized_predicates"]==["LIVEBENCH_IF_GE_65_7"]
    assert act["authority"]["global_fresh_reality"] is False
    assert act["exact_execution_binding"]["candidate_commit"]=="d5de4f5808dced840da34d051e3f9a5ff06e2e54"
    assert act["exact_execution_binding"]["population_count"]==200
    assert act["exact_execution_binding"]["threshold_percent"]==65.7

    print(json.dumps({
      "schema":"PROJECT_BRAIN_LIVEBENCH_CORRECTED_THRESHOLD_EXECUTOR_PUBLIC_VERIFIER_V1",
      "status":"PASS",
      "executor_git_blob_sha":EXEC_BLOB,
      "syntax_pass":True,
      "direct_execution_fail_closed":True,
      "exact_public_scorer_bindings_pass":True,
      "legacy_preprocessing_synthetic_pass":True,
      "ifbench_preprocessing_synthetic_pass":True,
      "release_date_dispatch_pass":True,
      "fixed_order_no_adaptive_selection_pass":True,
      "threshold_early_stop_pass":True,
      "raw_prompt_response_logging_absent":True,
      "point_of_use_preflight_precedes_dataset_read":True,
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "execution_authority_granted":False,
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
