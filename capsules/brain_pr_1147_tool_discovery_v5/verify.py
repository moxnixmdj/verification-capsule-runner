from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5

ROOT=Path(__file__).resolve().parent

def git_blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_baseline():
    p=ROOT/"baseline/current_main_tool_discovery_dynamic_candidate_v4.py"
    spec=importlib.util.spec_from_file_location("brain_main_v4",p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def base():
    return {
      "required_capabilities":["CAP_A"],"constraint":None,
      "visible_tools":[],"prior_probe_receipts":[],
      "discovery_sources":[],"discovery_receipts":[],
      "version_events":[],"decision_epoch":3,"source_set_digest":"",
    }

def source():
    return {"source_id":"AUTH","cost":0.0,"available":True,"authorized":True,
            "authoritative":True,"source_epoch":7,"source_digest":"sha256:s7"}

def receipt(tools,**kw):
    x={"kind":"DISCOVERY_RESULT","source_id":"AUTH","complete":True,
       "decision_epoch":3,"source_epoch":7,"source_digest":"sha256:s7",
       "source_set_digest":"sha256:set3","query":"CAP_A","tools":tools}
    x.update(kw); return x

def main():
    m=json.loads((ROOT/"manifest.json").read_text())
    for rel,want in m["exact_brain_blobs"].items():
        p=ROOT/rel if rel.startswith("baseline/") else ROOT/rel
        got=git_blob(p)
        assert got==want,(rel,want,got)

    v4=load_baseline()

    # Load-bearing counterexample against CURRENT main V4:
    # cheap route is unresolved and explicitly unsafe to probe; expensive route
    # is already proved. Selecting expensive is not a justified global least-cost claim.
    p=base()
    p["visible_tools"]=[
      {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,
       "epoch":0,"safe_probe_capabilities":[]},
      {"tool_id":"EXPENSIVE","cost":2.0,"available":True,"authorized":True,
       "epoch":0,"safe_probe_capabilities":["CAP_A"]},
    ]
    p["prior_probe_receipts"]=[
      {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE","capability":"CAP_A",
       "epoch":0,"supported":True}
    ]
    v4_action=v4.next_action(p)
    v5_action=v5.next_action(p)
    assert v4_action=={"action":"SELECT","tool_id":"EXPENSIVE"},v4_action
    assert v5_action=={
      "action":"ESCALATE",
      "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
      "tool_id":"CHEAP",
    },v5_action

    # Exact discovery receipt binding: stale/partial/wrong-query receipts cannot
    # count as discovery completion.
    q=base(); q["discovery_sources"]=[source()]; q["source_set_digest"]="sha256:set3"
    for mutation in (
      {"complete":False},{"decision_epoch":2},{"source_epoch":6},
      {"source_digest":"sha256:old"},{"source_set_digest":"sha256:old"},
      {"query":"CAP_B"},
    ):
        q["discovery_receipts"]=[receipt([],**mutation)]
        assert v5.next_action(q)=={"action":"DISCOVER","source_id":"AUTH","query":"CAP_A"},mutation

    # Once the exact complete interface is supplied and every unresolved route
    # is safe-probe decidable, V5 finds the actual global least-cost supported route.
    worlds=0
    for support in range(8):
      for avail in range(8):
       for auth in range(8):
        tools=[]
        for i,cost in enumerate((1.0,2.0,3.0)):
          tools.append({
            "tool_id":f"T{i}","cost":cost,
            "available":bool(avail&(1<<i)),"authorized":bool(auth&(1<<i)),
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
          })
        public=base()
        public["discovery_sources"]=[source()]
        public["source_set_digest"]="sha256:set3"
        public["discovery_receipts"]=[receipt(tools)]
        steps=0
        while steps<16:
          a=v5.next_action(public); steps+=1
          if a["action"]=="PROBE":
            i=int(a["tool_id"][1:])
            public["prior_probe_receipts"].append({
              "kind":"SAFE_CAPABILITY_PROBE","tool_id":a["tool_id"],
              "capability":"CAP_A","epoch":0,
              "supported":bool(support&(1<<i)),
            })
            continue
          eligible=[
            i for i in range(3)
            if bool(avail&(1<<i)) and bool(auth&(1<<i)) and bool(support&(1<<i))
          ]
          if eligible:
            assert a=={"action":"SELECT","tool_id":f"T{min(eligible)}"},(support,avail,auth,a)
          else:
            assert a["action"]=="ESCALATE",(support,avail,auth,a)
            assert a["reason"]=="NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"
          break
        else: raise AssertionError("ACTION_BUDGET")
        worlds+=1
    assert worlds==512

    print(json.dumps({
      "status":"INDEPENDENT_PASS__BRAIN_PR_1147_TOOL_DISCOVERY_V5_SOUNDNESS",
      "current_main_v4_counterexample_reproduced":True,
      "v5_counterexample_repaired_fail_closed":True,
      "complete_interface_worlds_checked":worlds,
      "exact_receipt_binding_checked":True,
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False
    },sort_keys=True,indent=2))

if __name__=="__main__":
    main()
