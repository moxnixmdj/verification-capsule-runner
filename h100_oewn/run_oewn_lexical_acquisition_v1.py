from __future__ import annotations

import json
from pathlib import Path

PRE=Path(__file__).resolve().parent/"H100_OEWN_LEXICAL_ACQUISITION_PREEXPOSURE_V1.json"

def main():
    import wn
    version=getattr(wn,"__version__",None)
    if version!="1.1.1":
        raise SystemExit(f"WN_VERSION_MISMATCH:{version}")
    pre=json.loads(PRE.read_text())
    if pre["source"]["lexicon"]!="oewn:2025":
        raise SystemExit("LEXICON_NOT_FROZEN")
    terms=pre["lemmas"]
    if len(terms)!=14 or len(terms)!=len(set(terms)):
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")

    wn.download("oewn:2025")
    lex=wn.Wordnet("oewn:2025")
    rows=[]
    missing=0
    poly=0
    unambiguous=0
    failures=0

    for lemma in terms:
        try:
            synsets=lex.synsets(lemma)
            count=len(synsets)
            ids=sorted(str(s.id) for s in synsets)
        except Exception as exc:
            failures+=1
            rows.append({"lemma":lemma,"query_status":"ERROR","error_type":type(exc).__name__})
            continue
        if count==0:
            missing+=1
            cls="MISSING"
        elif count==1:
            unambiguous+=1
            cls="ONE_SYNSET"
        else:
            poly+=1
            cls="POLYSEMOUS"
        rows.append({"lemma":lemma,"query_status":"OK","synset_count":count,"classification":cls,"synset_ids":ids})

    result={
      "schema":"PROJECT_BRAIN_H100_OEWN_LEXICAL_ACQUISITION_RESULT_V1",
      "source":{"lexicon":"oewn:2025","client_version":version},
      "term_count":len(terms),
      "missing_lemma_count":missing,
      "polysemous_lemma_count":poly,
      "unambiguous_lemma_count":unambiguous,
      "query_failure_count":failures,
      "rows":rows,
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "hard_nonclaims":[
        "LEXICAL_EXISTENCE_DOES_NOT_PROVE_TASK_ROLE",
        "POLYSEMY_REQUIRES_DISAMBIGUATION",
        "FINITE_LEMMA_COVERAGE_IS_NOT_OPEN_WORLD_COMPLETENESS"
      ]
    }
    print("H100_OEWN_RESULT="+json.dumps(result,sort_keys=True))
    if failures:
        raise SystemExit("OEWN_QUERY_FAILURES_PRESENT")

if __name__=="__main__":
    main()
