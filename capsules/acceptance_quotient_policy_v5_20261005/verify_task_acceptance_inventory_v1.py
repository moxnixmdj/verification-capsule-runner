from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.task_acceptance_quotient_inventory_v1 import compile_inventory

ROOT=Path(__file__).resolve().parent
EXPECTED_BLOBS={
    "canonical/runtime/task_acceptance_quotient_inventory_v1.py":"195ca8114f4018627bd4730e35d7d3911a2c4f83",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"a3fd20e58fdbd9b86278b7de0c245de3063dce27",
}
EXPECTED_OPUS={
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}
EXPECTED_TOP_SUPPORT={
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}

def blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def require(cond:bool,label:str)->None:
    if not cond:
        raise AssertionError(label)

def main()->None:
    for rel,sha in EXPECTED_BLOBS.items():
        require(blob(ROOT/rel)==sha,"BLOB_MISMATCH:"+rel)
    reg=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json").read_text())
    evid=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json").read_text())
    proved={x["predicate_id"] for x in evid["claims"] if x.get("state")=="PROVED"}
    out=compile_inventory(reg["predicates"],proved)
    require(out["open_predicate_count"]==24,"OPEN_COUNT")
    require(out["quotient_class_counts"]=={"H_SEPARATING":5,"M_RESTRICTED":2,"OTHER":17},"CLASS_COUNTS")
    require(set(out["opus_case_level_result_required"])==EXPECTED_OPUS,"OPUS_REQUIRED_SET")
    require(out["opus_case_level_result_required_count"]==5,"OPUS_REQUIRED_COUNT")
    require(out["opus_case_level_result_not_required_count"]==19,"TARGET_FREE_COUNT")
    rows={x["predicate_id"]:x for x in out["rows"]}
    require(set(x for x in EXPECTED_TOP_SUPPORT if rows[x]["quotient_class"]=="M_RESTRICTED")==EXPECTED_TOP_SUPPORT,"TOP_SUPPORT_SET")
    for pid in EXPECTED_TOP_SUPPORT:
        require(rows[pid]["opus_case_level_result_required"] is False,"TOP_SUPPORT_OPUS_DEP:"+pid)
    fixed=[x for x in out["rows"] if x["kind"]=="PUBLIC_FIXED_BAR"]
    require(len(fixed)==14,"FIXED_BAR_COUNT")
    require(all(x["opus_case_level_result_required"] is False for x in fixed),"FIXED_BAR_OPUS_DEP")
    print(json.dumps({
        "schema":"PROJECT_BRAIN_TASK_ACCEPTANCE_QUOTIENT_INVENTORY_PUBLIC_VERIFICATION_V1",
        "pass":True,
        "open_predicates":24,
        "quotient_class_counts":out["quotient_class_counts"],
        "opus_case_level_result_required_count":5,
        "opus_case_level_result_not_required_count":19,
        "opus_case_level_result_required":sorted(EXPECTED_OPUS),
        "target_free_zero_violation_atoms":sorted(EXPECTED_TOP_SUPPORT),
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
    },indent=2,sort_keys=True))

if __name__=="__main__":
    main()
