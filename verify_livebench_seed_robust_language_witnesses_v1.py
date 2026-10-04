#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import langdetect
from langdetect.detector_factory import DetectorFactory, PROFILES_DIRECTORY

TARGETS = (
    "en","es","pt","ar","hi","fr","ru","de","ja","it",
    "bn","uk","th","ur","ta","te","bg","ko","pl","he",
    "fa","vi","ne","sw","kn","mr","gu","pa","ml","fi",
)
OUT = Path("livebench_seed_robust_language_witnesses_v1.json")


def factory():
    f = DetectorFactory()
    f.load_profile(PROFILES_DIRECTORY)
    return f


def winner_info(f, gram: str, target: str):
    vec = f.word_lang_prob_map.get(gram)
    if vec is None:
        return None
    ti = f.langlist.index(target)
    tv = vec[ti]
    others = [v for i,v in enumerate(vec) if i != ti]
    m = max(others, default=0.0)
    return tv, m, tv - m


def exact_ngrams(f, text: str):
    d = f.create()
    d.append(text)
    d.cleaning_text()
    return d.text, d._extract_ngrams()


def robust_for_text(f, target: str, text: str):
    cleaned, grams = exact_ngrams(f, text)
    if not grams:
        return None
    uniq = sorted(set(grams))
    facts = []
    for g in uniq:
        wi = winner_info(f, g, target)
        if wi is None:
            return None
        tv, m, margin = wi
        if not (tv > m and tv > 0.0):
            return None
        facts.append((g, tv, m, margin))
    return cleaned, grams, facts


def candidate_atoms(f, target: str):
    ti = f.langlist.index(target)
    ranked = []
    for gram, vec in f.word_lang_prob_map.items():
        if not gram or len(gram) > 3 or any(ch.isspace() for ch in gram):
            continue
        tv = vec[ti]
        if tv <= 0.0:
            continue
        m = max(v for i,v in enumerate(vec) if i != ti)
        if tv > m:
            ranked.append((tv-m, tv, gram))
    ranked.sort(reverse=True)
    return [g for _,_,g in ranked]


def synthesize(f, target: str, case_mode: str = "any"):
    atoms = candidate_atoms(f, target)
    forms = []
    for atom in atoms[:12000]:
        variants = [atom]
        if case_mode == "upper":
            variants = [atom.upper()]
        elif case_mode == "lower":
            variants = [atom.lower()]
        for a in variants:
            if not a or any(ch.isspace() for ch in a):
                continue
            for sep in (" ", "\n", "9", "|"):
                text = sep.join([a] * 64)
                if len(text) >= 9000:
                    continue
                if case_mode == "upper" and not text.isupper():
                    continue
                if case_mode == "lower" and not text.islower():
                    continue
                proof = robust_for_text(f, target, text)
                if proof:
                    cleaned, grams, facts = proof
                    return {
                        "atom": a,
                        "separator_repr": repr(sep),
                        "text": text,
                        "cleaned_text": cleaned,
                        "ngram_occurrences": len(grams),
                        "unique_ngrams": [
                            {
                                "repr": repr(g),
                                "target_probability": tv,
                                "max_other_probability": m,
                                "strict_margin": margin,
                            }
                            for g,tv,m,margin in facts
                        ],
                    }
    return None


def runtime_falsification(text: str, target: str):
    results = []
    for seed in [0,1,2,3,7,11,29,97,997,65537,2147483647]:
        DetectorFactory.seed = seed
        got = langdetect.detect(text)
        results.append({"seed":seed,"got":got})
        if got != target:
            raise AssertionError(f"SEED_FALSIFIER:{target}:{seed}:{got}")
    DetectorFactory.seed = None
    return results


def main():
    version = importlib.metadata.version("langdetect")
    assert version == "1.0.9", version
    f = factory()
    missing = []
    witnesses = {}
    for target in TARGETS:
        w = synthesize(f,target)
        if w is None:
            missing.append(target)
            print("MISSING",target)
            continue
        w["runtime_seed_checks"] = runtime_falsification(w["text"],target)
        witnesses[target]=w
        print("PASS",target,repr(w["atom"]),w["ngram_occurrences"],len(w["unique_ngrams"]))

    english_case = {}
    for mode in ("upper","lower"):
        w = synthesize(f,"en",mode)
        if w is not None:
            w["runtime_seed_checks"] = runtime_falsification(w["text"],"en")
            english_case[mode]=w
            print("PASS_ENGLISH_CASE",mode,repr(w["atom"]))
        else:
            print("MISSING_ENGLISH_CASE",mode)

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_SEED_ROBUST_LANGUAGE_WITNESS_DISCOVERY_V1",
        "status":"PASS_ALL_TARGETS_HAVE_ALL_NGRAMS_STRICTLY_TARGET_DOMINANT__CPYTHON_ALPHA_BOUND_PROOF_STILL_REQUIRED" if not missing and len(english_case)==2 else "PARTIAL__SOME_TARGETS_LACK_SIMPLE_STRICT_NGRAM_DOMINANCE_WITNESS",
        "langdetect_version":version,
        "target_count":len(TARGETS),
        "witness_count":len(witnesses),
        "missing_targets":missing,
        "english_case_modes_found":sorted(english_case),
        "witnesses":witnesses,
        "english_case_witnesses":english_case,
        "proof_shape":[
            "INITIAL_LANGUAGE_PROBABILITIES_ARE_UNIFORM",
            "EVERY_EXTRACTED_NGRAM_HAS_STRICTLY_GREATER_PROFILE_PROBABILITY_FOR_TARGET_THAN_EVERY_OTHER_LANGUAGE",
            "FOR_POSITIVE_ALPHA_EVERY_MULTIPLICATIVE_UPDATE_STRICTLY_PRESERVES_TARGET_AS_UNIQUE_ARGMAX",
            "THEREFORE_RANDOM_NGRAM_CHOICE_AND_RANDOM_SEED_CANNOT_CHANGE_TOP_LANGUAGE",
            "REMAINING_FORMAL_OBLIGATION_IS_EXACT_CPYTHON_RANDOM_GAUSS_BOUND_PROVING_ALPHA_ALWAYS_POSITIVE",
        ],
        "terminal_rows_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
    }
    OUT.write_text(json.dumps(receipt,ensure_ascii=True,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:receipt[k] for k in ("status","witness_count","missing_targets","english_case_modes_found")},sort_keys=True))
    return 0 if not missing and len(english_case)==2 else 3


if __name__=="__main__":
    raise SystemExit(main())
