from __future__ import annotations

import copy
import importlib.util
import json
import sys
from hashlib import sha1
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
    "v22_prewrite_admission.py":"fe2c8719a1e78ff8c6193e711868605d7f3fa723",
    "terminal_progress_enforcement.py":"b79494e101b41e42354b93cf3c5196c895bbb75b",
    "enforce_terminal_progress_pr_v1.py":"ad75394f5d3d3158a4b3d80ef552ecc6e0e99124",
    "source_test_v22.py":"2a7e7b7405925418fd392fac86961bc4d8c7aa40",
    "source_test_progress.py":"90b216d76cfe89b932a39cd67e9ae73dd01dcd1a",
    "governance.json":"6e565c5123a33c966d375e61dacbac24796ef86b",
    "terminal_progress_delta_gate_v1.py":"1282ed322fcb7b1b1889000778966da3572020db",
}
A40="a"*40
B40="b"*40

def blob(path: Path) -> str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(name: str,path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def main():
    observed={name:blob(ROOT/name) for name in EXPECTED}
    assert observed==EXPECTED,(observed,EXPECTED)

    gate=load("trusted_terminal_progress_delta_gate",ROOT/"terminal_progress_delta_gate_v1.py")
    progress=load("terminal_progress_enforcement_verified",ROOT/"terminal_progress_enforcement.py")
    v22=load("v22_prewrite_admission_verified",ROOT/"v22_prewrite_admission.py")
    compile(ROOT/"enforce_terminal_progress_pr_v1.py".read_text() if False else "", "<noop>", "exec")
    compile((ROOT/"enforce_terminal_progress_pr_v1.py").read_text(),str(ROOT/"enforce_terminal_progress_pr_v1.py"),"exec")

    gov=json.loads((ROOT/"governance.json").read_text())
    assert gov["schema"]=="PROJECT_BRAIN_V22_TERMINAL_PROGRESS_ENFORCEMENT_V1"
    assert gov["accounting"]["acceptance_credit_delta"]==0
    assert gov["accounting"]["family_credit_delta"]==0
    assert gov["accounting"]["capability_credit_delta"]==0
    assert gov["accounting"]["ownership_credit_delta"]==0
    assert gov["hard_boundary"]["provider_branch_protection_or_required_check_configuration_available"] is False
    assert gov["hard_boundary"]["existing_drift_guard_weakened"] is False

    checks=[]
    def ok(name,condition):
        assert condition,name
        checks.append(name)

    pointer={
        "exact_state":{
            "accepted_families":5,"open_families":14,"proved_atomic":14,"unresolved_atomic":24,
            "root1_positive_gap_count":0,"root2_touching_count":18,"root3_touching_count":9,
            "meta_envelope_open_count":8,"total_open_truth_obligations":32,"terminal":False,
        },
        "current_shared_causal_interfaces":["EXTERNAL_RESULT_OR_ACCESS","UNIVERSAL_SCOPE_AND_COMPOSITION","BEHAVIORAL_QUOTIENT_AND_TRANSFER"],
        "dormant_wake_only":["HLE_GRADER_RELATION"],
        "meta_dormant_wake_only":["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR"],
    }
    targets=["COMPOSITION_COMPONENT_SCOPED_PROOFS"]
    admission={
        "active_pointer_path":v22.ACTIVE_POINTER_PATH,
        "active_pointer_git_blob_sha":"1"*40,
        "mode":"ACTIVE_INTERFACE",
        "interface":"UNIVERSAL_SCOPE_AND_COMPOSITION",
        "target_truth_obligations":targets,
        "proof_state_reachability":"CURRENT_ROOT3",
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
        "claimed_progress_credit":0,
        "work_class":"PROGRESS_CANDIDATE",
        "postchange_evidence_required":True,
        "expected_progress":{
            "effect_kind":"PROOF_NODE_CONTRACTION",
            "target_truth_obligations":targets,
            "success_condition":"ACTIVE_CLAIM_CLOSES",
        },
        "currentness":dict(pointer["exact_state"]),
        "tournament":{
            "proposal_id":"P","falsifier_id":"F","decisive_question":"Q",
            "known_counterexamples_checked":True,
            "counterexample_receipts":[{"path":"counter.json","git_blob_sha":"2"*40}],
        },
    }
    errors=v22.admission_errors(
        admission,pointer,pointer_blob_sha="1"*40,action_kind="RECONCILE_FRONTIER",
        receipt_blobs={"counter.json":"2"*40},
    )
    ok("PROGRESS_CANDIDATE_PREWRITE_PASS",errors==[])

    bad=copy.deepcopy(admission); bad.pop("work_class")
    ok("UNCLASSIFIED_WORK_FAILS_CLOSED","V22_WORK_CLASS_INVALID" in v22.admission_errors(
        bad,pointer,pointer_blob_sha="1"*40,action_kind="RECONCILE_FRONTIER",receipt_blobs={"counter.json":"2"*40}
    ))
    bad=copy.deepcopy(admission); bad["expected_progress"]["target_truth_obligations"]=["OTHER"]
    ok("EXPECTED_TARGET_DRIFT_FAILS_CLOSED","V22_EXPECTED_PROGRESS_TARGET_MISMATCH" in v22.admission_errors(
        bad,pointer,pointer_blob_sha="1"*40,action_kind="RECONCILE_FRONTIER",receipt_blobs={"counter.json":"2"*40}
    ))
    bad=copy.deepcopy(admission); bad["work_class"]="CONTROL_PLANE"; bad.pop("expected_progress"); bad.pop("postchange_evidence_required")
    ok("CONTROL_PLANE_CLASS_CANNOT_ESCAPE_MODE","V22_CONTROL_PLANE_WORK_CLASS_OUTSIDE_CONTROL_PLANE_MODE" in v22.admission_errors(
        bad,pointer,pointer_blob_sha="1"*40,action_kind="RECONCILE_FRONTIER",receipt_blobs={"counter.json":"2"*40}
    ))
    repair=copy.deepcopy(admission); repair["work_class"]="TRUTH_REPAIR"; repair.pop("expected_progress"); repair["tournament"]["counterexample_receipts"]=[]; repair["tournament"]["no_known_counterexample_reason"]="NONE"
    ok("TRUTH_REPAIR_REQUIRES_COUNTERMODEL","V22_TRUTH_REPAIR_COUNTERMODEL_RECEIPT_REQUIRED" in v22.admission_errors(
        repair,pointer,pointer_blob_sha="1"*40,action_kind="RECONCILE_FRONTIER",receipt_blobs={}
    ))

    def synthetic_docs():
        p={
            "exact_state":{"unresolved_atomic":3,"meta_envelope_open_count":3,"total_open_truth_obligations":6},
            "current_shared_causal_interfaces":["I1","I2"],
            "meta_dormant_wake_only":["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR"],
        }
        root={"current_residual_root_partition":{
            "unresolved_total":3,"root1_only":[],"root2_only":["A"],"root3_only":["B"],"root2_and_root3":["C"]
        }}
        tour={"proposals":[{"interface":"BEHAVIORAL_QUOTIENT_AND_TRANSFER","target_obligations":["CYBERSECURITY","LONG_CONTEXT"]}]}
        loop={"claims":[
            {"id":"C0","status":"PROVED","depends_on":[]},
            {"id":"C1","status":"ACTIVE","depends_on":["C0"]},
            {"id":"C2","status":"ACTIVE","depends_on":["C1"]},
        ]}
        return {
            progress.POINTER_PATH:p,progress.ROOT_STATE_PATH:root,
            progress.TOURNAMENT_PATH:tour,progress.CONTROL_LOOP_PATH:loop,
        }

    before_docs=synthetic_docs()
    before=progress.compile_canonical_state(
        pointer=before_docs[progress.POINTER_PATH],
        root_state=before_docs[progress.ROOT_STATE_PATH],
        tournament=before_docs[progress.TOURNAMENT_PATH],
        control_loop=before_docs[progress.CONTROL_LOOP_PATH],
    )
    ok("CANONICAL_STATE_DERIVES_SIX_TRUTHS",len(before["open_truth_obligations"])==6)
    ok("CANONICAL_STATE_DERIVES_ACTIVE_DAG",before["max_open_causal_depth"]==2 and before["open_proof_node_count"]==2 and before["open_prerequisites"]==["C1"])

    after_docs=copy.deepcopy(before_docs)
    after_docs[progress.CONTROL_LOOP_PATH]["claims"][2]["status"]="PROVED"
    after=progress.compile_canonical_state(
        pointer=after_docs[progress.POINTER_PATH],
        root_state=after_docs[progress.ROOT_STATE_PATH],
        tournament=after_docs[progress.TOURNAMENT_PATH],
        control_loop=after_docs[progress.CONTROL_LOOP_PATH],
    )
    t=["C"]
    binding={
        "before_state_sha256":before["state_sha256"],
        "after_state_sha256":after["state_sha256"],
        "target_truth_obligations_sha256":gate.sha256_json(sorted(t)),
        "effect_kind":"DEPTH_CONTRACTION",
    }
    row={"path":"receipt.json","git_blob_sha":A40,**binding}
    result=progress.evaluate_postchange(
        work_class="PROGRESS_CANDIDATE",target_truth_obligations=t,
        before_documents=before_docs,after_documents=after_docs,
        evidence_record={"evidence_receipts":[row]},
        resolve_receipt=lambda path:(dict(binding),A40),
    )
    ok("CANONICAL_POSTCHANGE_CONTRACTION_PASS",result["gate_result"]["status"]=="ADMIT_TERMINAL_CONTRACTING_PROGRESS")

    try:
        progress.evaluate_postchange(
            work_class="PROGRESS_CANDIDATE",target_truth_obligations=t,
            before_documents=before_docs,after_documents=after_docs,
            evidence_record={"evidence_receipts":[row]},
            resolve_receipt=lambda path:(dict(binding),B40),
        )
        raise AssertionError("UNRELATED_BLOB_SHOULD_FAIL")
    except progress.TerminalProgressEnforcementError as exc:
        ok("UNRELATED_RECEIPT_BLOB_FAILS_CLOSED","BLOB_MISMATCH" in str(exc))

    wrong=dict(binding); wrong["effect_kind"]="TRUTH_CLOSURE"
    try:
        progress.evaluate_postchange(
            work_class="PROGRESS_CANDIDATE",target_truth_obligations=t,
            before_documents=before_docs,after_documents=after_docs,
            evidence_record={"evidence_receipts":[row]},
            resolve_receipt=lambda path:(wrong,A40),
        )
        raise AssertionError("CONTENT_DRIFT_SHOULD_FAIL")
    except progress.TerminalProgressEnforcementError as exc:
        ok("RECEIPT_CONTENT_BINDING_FAILS_CLOSED","CONTENT_BINDING_MISMATCH" in str(exc))

    repair_after=copy.deepcopy(before_docs)
    repair_after[progress.CONTROL_LOOP_PATH]["claims"].append({"id":"C3","status":"ACTIVE","depends_on":[]})
    repair_state=progress.compile_canonical_state(
        pointer=repair_after[progress.POINTER_PATH],
        root_state=repair_after[progress.ROOT_STATE_PATH],
        tournament=repair_after[progress.TOURNAMENT_PATH],
        control_loop=repair_after[progress.CONTROL_LOOP_PATH],
    )
    rbinding={
        "before_state_sha256":before["state_sha256"],
        "after_state_sha256":repair_state["state_sha256"],
        "target_truth_obligations_sha256":gate.sha256_json(sorted(t)),
        "effect_kind":"TRUTH_REPAIR",
    }
    rrow={"path":"countermodel.json","git_blob_sha":A40,**rbinding}
    repaired=progress.evaluate_postchange(
        work_class="TRUTH_REPAIR",target_truth_obligations=t,
        before_documents=before_docs,after_documents=repair_after,
        evidence_record={"countermodel_receipts":[rrow]},
        resolve_receipt=lambda path:(dict(rbinding),A40),
    )
    ok("TRUTH_REPAIR_ZERO_PROGRESS",repaired["gate_result"]["status"]=="ADMIT_TRUTH_REPAIR_NOT_PROGRESS" and repaired["gate_result"]["counts_as_progress"] is False)

    bad_docs=synthetic_docs()
    bad_docs[progress.POINTER_PATH]["exact_state"]["total_open_truth_obligations"]=7
    try:
        progress.compile_canonical_state(
            pointer=bad_docs[progress.POINTER_PATH],root_state=bad_docs[progress.ROOT_STATE_PATH],
            tournament=bad_docs[progress.TOURNAMENT_PATH],control_loop=bad_docs[progress.CONTROL_LOOP_PATH],
        )
        raise AssertionError("FABRICATED_COUNT_SHOULD_FAIL")
    except progress.TerminalProgressEnforcementError as exc:
        ok("FABRICATED_CANONICAL_COUNT_FAILS_CLOSED","GLOBAL_OPEN_TRUTH_COUNT_MISMATCH" in str(exc))

    print(json.dumps({
        "schema":"PROJECT_BRAIN_V22_TERMINAL_PROGRESS_ENFORCEMENT_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS__EXACT_BLOBS__TWO_STAGE_CLASSIFICATION_CANONICAL_STATE_DERIVATION_AND_RECEIPT_BINDING_VERIFIED__ZERO_CREDIT",
        "exact_source_git_blob_shas":EXPECTED,
        "checks":checks,
        "check_count":len(checks),
        "accounting":{
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        },
    },indent=2,sort_keys=True))

if __name__=="__main__":
    main()
