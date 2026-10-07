from __future__ import annotations
import hashlib, importlib.util, itertools, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "candidate_source.py": "ea8057b0eadac210c4f4378298df93ed233c5824",
    "evaluator_source.py": "9d3d9bb837a98a7f78b5794cec0c0ae88bb32860",
    "theorem.json": "0ccc3ecbdbf2636b8f1e7f0daf959a48350cb82e",
}

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC_FAILED:" + name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def utility(s, r, a, v):
    return (5 if s else -12) + (4 if r and v else 0) + (3 if a else -1) + (2 if v else 0)

def main():
    for name, expected in EXPECTED.items():
        got = blob_sha(HERE / name)
        assert got == expected, (name, got, expected)

    candidate_text = (HERE / "candidate_source.py").read_text()
    evaluator_text = (HERE / "evaluator_source.py").read_text()
    theorem = json.loads((HERE / "theorem.json").read_text())

    for snippet in (
        'grounded=bool(claims) and all(x in facts for x in claims)',
        'fit=str(e.get("intended_audience") or "")==audience',
        '(5 if grounded else -12)',
        '+(4 if grounded and topic in required and analysis!="layout" else 0)',
        '+(3 if fit else -1)',
        '+(2 if analysis!="layout" else 0)',
        'if estimate(x)>0 and str(x.get("analysis_kind") or "")!="layout"',
        'score-=20*len(required-covered)',
        'key=(-score,cost,ids)',
    ):
        assert snippet in candidate_text, "CANDIDATE_SEMANTIC_ANCHOR_MISSING:" + snippet

    for snippet in (
        '{"fact_id":f"F{i}","topic":f"T{i%3}"',
        'facts if f["topic"]==topic',
        'claims=refs[:1]',
        'claims=[f"UNSUPPORTED-{i}"]',
        '"supported":supported',
        '"required_topic":topic in required_topics',
        '"audience_fit":intended_audience==audience',
        '"analysis_value":analysis_kind!="layout"',
        '(5 if h["supported"] else -12)',
        '+(4 if h["required_topic"] and h["analysis_value"] else 0)',
        '+(3 if h["audience_fit"] else -1)',
        '+(2 if h["analysis_value"] else 0)',
        'if hidden[x["id"]]["supported"] and hidden[x["id"]]["analysis_value"]',
        'score-=20*len(missing)',
        'key=(-score,cost,ids)',\n        'best=(key,ids,score,cost,sorted(missing))',
    ):
        assert snippet in evaluator_text, "EVALUATOR_SEMANTIC_ANCHOR_MISSING:" + snippet

    rows=[]
    for s,r,a,v in itertools.product((False,True), repeat=4):
        u=utility(s,r,a,v)
        rows.append((s,r,a,v,u,(u>0 and v),(s and v)))
    assert all(x[5] == x[6] for x in rows), rows
    assert max(x[4] for x in rows if not x[0]) == -3
    assert min(x[4] for x in rows if x[0] and x[3]) == 6

    for difficulty in range(1,6):
        fact_count=4+difficulty
        facts=[(f"F{i}",f"T{i%3}") for i in range(fact_count)]
        assert {t for _,t in facts} == {"T0","T1","T2"}
        ids={fid for fid,_ in facts}
        for topic in {"T0","T1","T2"}:
            refs=sorted(fid for fid,t in facts if t==topic)
            assert refs and refs[0] in ids
        for i in range(5+difficulty):
            assert f"UNSUPPORTED-{i}" not in ids

    candidate=load("candidate_source","candidate_source.py")
    evaluator=load("evaluator_source","evaluator_source.py")

    checked=0
    for difficulty in range(1,6):
        for seed in range(-128,128):
            case=evaluator.generate_case(evaluator.P2,seed,difficulty)
            got=candidate.solve(evaluator.public_task(case))
            verdict=evaluator.score_case(case,got)
            assert verdict["pass"] is True, (seed,difficulty,verdict,got,case["_oracle"])
            checked += 1

    assert theorem["schema"] == "PROJECT_BRAIN_P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_V1"
    assert theorem["target"]["exact_domain"] == "ALL_CASES_EMITTED_BY_p2_p3_information_safe_proof_suites_v2::_p2_FOR_ANY_INTEGER_SEED_AND_DIFFICULTY_1_THROUGH_5"
    assert theorem["target"]["claim"] == "THE_BOUND_BRAIN_CANDIDATE_RETURNS_THE_EXACT_HIDDEN_ORACLE_SELECTED_EDIT_SET_FOR_EVERY_CASE_IN_THIS_EXACT_GENERATOR_DOMAIN"
    assert theorem["abc_consequence"]["selected_cell_scope_complete"] is True
    assert theorem["abc_consequence"]["artifact_family_closed"] is False
    assert theorem["abc_consequence"]["professional_quality_global_closed"] is False
    assert "NO_CLAIM_THE_SYNTHETIC_P2_GENERATOR_IS_SCOPE_EQUIVALENT_TO_ALL_REALISTIC_PROFESSIONAL_DELIVERABLES" in theorem["hard_nonclaims"]

    print(json.dumps({
        "status":"PASS",
        "canonical_brain_cell":"P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1",
        "verified":[
            "EXACT_CANONICAL_THEOREM_CANDIDATE_AND_EVALUATOR_BLOBS_MATCH",
            "HIDDEN_FACTOR_RECOVERY_MATCHES_EXACT_PINNED_SOURCE",
            "ALL_16_BOOLEAN_FACTOR_ASSIGNMENTS_PROVE_COVERAGE_EQUIVALENCE",
            "UNSUPPORTED_MAX_UTILITY_IS_MINUS_3",
            "SUPPORTED_ANALYTICAL_MIN_UTILITY_IS_6",
            "ALL_ALLOWED_DIFFICULTIES_HAVE_NONEMPTY_PER_TOPIC_FACT_SUPPORT",
            "UNSUPPORTED_IDS_ARE_DISJOINT_FROM_FACT_IDS",
            "1280_EXECUTABLE_SEED_DIFFICULTY_CANARIES_PASS",
            "UNIVERSAL_SELECTED_CELL_IS_SOURCE_STRUCTURAL_NOT_SAMPLE_INFERENCE",
            "OPEN_ENDED_REALISTIC_PROFESSIONAL_SCOPE_REMAINS_OPEN",
            "ZERO_TERMINAL_CREDIT"
        ],
        "canary_cases":checked,
        "terminal_credit_delta":0
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
