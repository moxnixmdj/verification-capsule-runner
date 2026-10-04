from __future__ import annotations
import hashlib, importlib, json
from pathlib import Path
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/tests/test_unknown_domain_direct_hidden_generator_v2.py":"c4d8f9e1c7f4a6ba104d06a10255b50d7f499e97",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V2.json":"6bf6042a7a36c12d6d5ebfc5d16ea23ed2befbb6",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V1.json":"26108d0d06f7a308c3eaf4b9821ff0c4551dcda3",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
}
def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def exact_bytes():
    for p,s in EXPECTED.items():
        got=git_blob((ROOT/p).read_bytes()); assert got==s,(p,got,s)
def copied_tests():
    mod=importlib.import_module("canonical.tests.test_unknown_domain_direct_hidden_generator_v2")
    names=sorted(n for n in dir(mod) if n.startswith("test_") and callable(getattr(mod,n)))
    for n in names: getattr(mod,n)()
    return names
def fresh():
    a=v2.generate_qualification_fixture_population(beacon="independent-fresh-beacon-0001")
    b=v2.generate_qualification_fixture_population(beacon="independent-fresh-beacon-0002")
    assert a["visible_packet_digest"]!=b["visible_packet_digest"]
    assert a["hidden_packet_digest"]!=b["hidden_packet_digest"]
    assert a["production"] is False and b["production"] is False
    d=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V2.json").read_text())
    assert d["accounting"]["generated_production_case_count"]==0
    assert d["accounting"]["terminal_cases_consumed"]==0
    assert d["accounting"]["new_reality_units_consumed"]==0
if __name__=="__main__":
    exact_bytes(); names=copied_tests(); fresh()
    print(json.dumps({"status":"PASS","exact_blob_count":len(EXPECTED),"copied_tests_passed":len(names),"fresh_beacon_resampling":"PASS","generated_production_cases":0,"candidate_bound":False,"acceptance_credit_delta":0},sort_keys=True))
