from __future__ import annotations
import hashlib, importlib.util, json, sys, types
from collections import Counter
from pathlib import Path

ROOT=Path("capsules/saccr_corrected_launcher_v1")
MANIFEST=ROOT/"input.json"
SPECIMEN=ROOT/"terminal_parent_portfolio_launcher_v1.py"

def git_blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+bytes([0])+data).hexdigest()

def install_runtime_stub(runtime, name, attrs):
    m=types.ModuleType("canonical.runtime."+name)
    for k,v in attrs.items():
        setattr(m,k,v)
    setattr(runtime,name,m)
    sys.modules["canonical.runtime."+name]=m
    return m

def main() -> int:
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual=git_blob(SPECIMEN)
    assert actual==manifest["expected_source_blob_sha"],(actual,manifest["expected_source_blob_sha"])
    assert actual==manifest["source_blob_sha"]

    canonical=types.ModuleType("canonical"); canonical.__path__=[]
    runtime=types.ModuleType("canonical.runtime"); runtime.__path__=[]
    sys.modules["canonical"]=canonical
    sys.modules["canonical.runtime"]=runtime
    canonical.runtime=runtime

    SA="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
    CAD="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
    BROWSER="BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001"
    DELEG="TASK_TO_DELEGATION_GRAPH_001"
    TOOL="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
    RESEARCH="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001"

    direct=install_runtime_stub(runtime,"direct_route_terminal_executors_v1",{
        "BROWSER_ID":BROWSER,
        "DELEGATION_ID":DELEG,
        "TOOL_ID":TOOL,
        "RESEARCH_ID":RESEARCH,
        "bound_behavior_ids":lambda:[SA,BROWSER,DELEG,TOOL,RESEARCH],
        "execute_direct_route":lambda *a,**k:None,
    })
    saccr=install_runtime_stub(runtime,"saccr_route_specific_terminal_executor_v1",{
        "BEHAVIOR_ID":SA,
        "SAMPLE_COUNT":2000,
        "execute_terminal":lambda **k:None,
    })
    install_runtime_stub(runtime,"cad_t0_route_specific_terminal_executor_v1",{
        "BEHAVIOR_ID":CAD,
        "execute_cad_route":lambda **k:None,
    })

    bindings={
        CAD:{"portfolios":["T0"],"binding_blob":"cad"},
        "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":{"portfolios":["T0"],"binding_blob":"traj"},
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":{"portfolios":["T1"],"binding_blob":"plan"},
        "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":{"portfolios":["T1"],"binding_blob":"artifact"},
        "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":{"portfolios":["T1","T3"],"binding_blob":"synth"},
        "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT_001":{"portfolios":["T2"],"binding_blob":"scope"},
        "UNKNOWN_DOMAIN_ADAPTATION_001":{"portfolios":["T3"],"binding_blob":"unknown"},
    }
    multiplex=install_runtime_stub(runtime,"portfolio_multiplex_terminal_instrumentation_v1",{
        "BINDINGS":bindings,
        "bound_behavior_ids":lambda:list(bindings),
        "validate_parent_observation":lambda behavior_id,row:{"valid":True,"errors":[]},
        "reduce_behavior_receipts":lambda behavior_id,rows:{"status":"PASS_COMPONENT","behavior_id":behavior_id,"count":len(rows)},
    })

    authority_state={"value":True}
    install_runtime_stub(runtime,"terminal_wave_launch_authority_reducer_v1",{
        "evaluate":lambda root:{"launch_authority":authority_state["value"]}
    })
    install_runtime_stub(runtime,"terminal_parent_portfolio_runner_v1",{
        "execute_parent_portfolio":lambda *a,**k:[]
    })

    spec=importlib.util.spec_from_file_location(
        "canonical.runtime.terminal_parent_portfolio_launcher_v1",SPECIMEN
    )
    launcher=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=launcher
    setattr(runtime,"terminal_parent_portfolio_launcher_v1",launcher)
    assert spec.loader is not None
    spec.loader.exec_module(launcher)

    pre=launcher.static_route_preflight()
    assert pre["pass"],pre
    assert pre["active_contract_count"]==12,pre
    assert pre["direct_multiplex_overlap"]==[CAD],pre
    assert launcher.DIRECT_PORTFOLIOS[SA]==("T1",)
    assert set(launcher.DIRECT_PORTFOLIOS)==set(direct.bound_behavior_ids())|{CAD}

    commitment="frozen-package"
    beacon="post-freeze-beacon"
    direct_calls=Counter()
    parent_calls=Counter()
    saccr_kwargs=[]

    def direct_runner(behavior_id,**kwargs):
        assert behavior_id not in {SA,CAD}
        direct_calls[behavior_id]+=1
        return {"behavior_id":behavior_id,"pass":True,"terminal_result":True}

    def saccr_runner(**kwargs):
        saccr_kwargs.append(dict(kwargs))
        direct_calls[SA]+=1
        return {
            "status":"PASS",
            "all_pass":True,
            "case_count":2000,
            "terminal_authority":True,
            "fresh_terminal_evidence_consumed":2000,
        }

    def cad_runner(**kwargs):
        direct_calls[CAD]+=1
        return {"behavior_id":CAD,"pass":True,"terminal_result":True}

    def parent_runner(portfolio,**kwargs):
        parent_calls[portfolio]+=1
        assert kwargs["commitment"]==commitment
        assert kwargs["beacon"]==beacon
        rows=[]
        for behavior_id,binding in bindings.items():
            if portfolio in binding["portfolios"]:
                rows.append({
                    "behavior_id":behavior_id,
                    "portfolio":portfolio,
                    "case_id":portfolio+"::"+behavior_id+"::0",
                    "candidate_package_commitment":commitment,
                    "post_freeze_beacon":beacon,
                    "binding_blob":binding["binding_blob"],
                    "load_bearing":True,
                })
        return rows

    out=launcher.execute_wave(
        commitment=commitment,
        beacon=beacon,
        parent_runner=parent_runner,
        direct_runner=direct_runner,
        saccr_runner=saccr_runner,
        cad_runner=cad_runner,
        root=Path("."),
    )
    assert out["pass"],out
    row=out["direct_results"][SA]
    assert row["behavior_id"]==SA
    assert row["pass"] is True
    assert row["terminal_result"] is True
    assert row["case_count"]==2000
    assert len(saccr_kwargs)==1
    assert saccr_kwargs[0]["candidate_package_commitment"]==commitment
    assert saccr_kwargs[0]["post_freeze_beacon"]==beacon
    assert "commitment" not in saccr_kwargs[0] and "beacon" not in saccr_kwargs[0]
    assert set(direct_calls)==set(launcher.DIRECT_PORTFOLIOS)
    assert all(n==1 for n in direct_calls.values()),direct_calls
    assert parent_calls==Counter({"T0":1,"T1":1,"T2":1,"T3":1}),parent_calls
    assert out["shared_direct_route_duplicate_execution_count"]==0

    authority_state["value"]=False
    forbidden_calls={"n":0}
    def forbidden(*a,**k):
        forbidden_calls["n"]+=1
        raise AssertionError("runner invoked without launch authority")
    blocked=launcher.execute_wave(
        commitment=commitment,
        beacon=beacon,
        parent_runner=forbidden,
        direct_runner=forbidden,
        saccr_runner=forbidden,
        cad_runner=forbidden,
        root=Path("."),
    )
    assert blocked["pass"] is False
    assert blocked["status"]=="FAIL_CLOSED_LAUNCH_NOT_AUTHORIZED"
    assert blocked["parent_runner_invoked"] is False
    assert blocked["direct_runner_invoked"] is False
    assert forbidden_calls["n"]==0

    print("SACCR_CORRECTED_LAUNCHER_V1_PASS",actual)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
