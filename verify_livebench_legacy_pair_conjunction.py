#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import sys
import tempfile
import urllib.request

BRAIN_COMMIT = "410579713f89ba64a542870b0820dbb23581b3e8"
SOLVER_PATH = "canonical/runtime/livebench_legacy_ifeval_constructive_solver_v1.py"
SOLVER_BLOB = "c293426df092ca1b82d77aa194ef182b510a0294"
INVERTER_PATH = "canonical/runtime/livebench_legacy_ifeval_prompt_inverter_v1.py"
INVERTER_BLOB = "74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a"

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM = {
    "instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
}

BASE_REQUEST = "Explain why deterministic verification matters"

SAMPLE_ARGS = {
    "keywords:existence":{"keywords":["alpha","beta"]},
    "keywords:frequency":{"keyword":"alpha","frequency":3,"relation":"at least"},
    "keywords:forbidden_words":{"forbidden_words":["omega","zeta"]},
    "keywords:letter_frequency":{"letter":"q","let_frequency":4,"let_relation":"less than"},
    "language:response_language":{"language":"en"},
    "length_constraints:number_sentences":{"num_sentences":4,"relation":"at least"},
    "length_constraints:number_paragraphs":{"num_paragraphs":3},
    "length_constraints:number_words":{"num_words":17,"relation":"at least"},
    "length_constraints:nth_paragraph_first_word":{"num_paragraphs":3,"nth_paragraph":2,"first_word":"alpha"},
    "detectable_content:number_placeholders":{"num_placeholders":3},
    "detectable_content:postscript":{"postscript_marker":"P.S."},
    "detectable_format:number_bullet_lists":{"num_bullets":4},
    "detectable_format:constrained_response":{},
    "detectable_format:number_highlighted_sections":{"num_highlights":3},
    "detectable_format:multiple_sections":{"section_spliter":"Section","num_sections":3},
    "detectable_format:json_format":{},
    "detectable_format:title":{},
    "combination:two_responses":{},
    "combination:repeat_prompt":{"prompt_to_repeat":BASE_REQUEST},
    "startend:end_checker":{"end_phrase":"THE END"},
    "change_case:capital_word_frequency":{"capital_frequency":3,"capital_relation":"at least"},
    "change_case:english_capital":{},
    "change_case:english_lowercase":{},
    "punctuation:no_comma":{},
    "startend:quotation":{},
}

def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def fetch(url: str, expected: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-pair-conjunction-verifier"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    got = blob_sha(raw)
    assert got == expected, (url, got, expected)
    return raw

def write(path: pathlib.Path, raw: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)

with tempfile.TemporaryDirectory() as td_s:
    td = pathlib.Path(td_s)
    cand = td / "candidate"
    (cand/"canonical"/"runtime").mkdir(parents=True)
    (cand/"canonical"/"__init__.py").write_text("", encoding="utf-8")
    (cand/"canonical"/"runtime"/"__init__.py").write_text("", encoding="utf-8")

    solver_raw = fetch(
        f"https://raw.githubusercontent.com/moxnixmdj/brain/{BRAIN_COMMIT}/{SOLVER_PATH}",
        SOLVER_BLOB,
    )
    inverter_raw = fetch(
        f"https://raw.githubusercontent.com/moxnixmdj/brain/{BRAIN_COMMIT}/{INVERTER_PATH}",
        INVERTER_BLOB,
    )
    write(cand/SOLVER_PATH, solver_raw)
    write(cand/INVERTER_PATH, inverter_raw)

    up = td / "upstream"
    pkg = up / "instruction_following_eval"
    pkg.mkdir(parents=True)
    (pkg/"__init__.py").write_text("", encoding="utf-8")
    observed = {}
    for name, expected in UPSTREAM.items():
        raw = fetch(
            f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval/{name}",
            expected,
        )
        observed[name] = blob_sha(raw)
        write(pkg/name, raw)

    sys.path.insert(0, str(cand))
    sys.path.insert(0, str(up))

    # Keep language detection deterministic when exercised.
    try:
        from langdetect import DetectorFactory
        DetectorFactory.seed = 0
    except Exception:
        pass
    try:
        import nltk
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
    except Exception:
        pass

    solver = importlib.import_module("canonical.runtime.livebench_legacy_ifeval_constructive_solver_v1")
    registry = importlib.import_module("instruction_following_eval.instructions_registry")

    active = list(registry.INSTRUCTION_DICT.keys())
    assert len(active) == 25, len(active)
    assert set(active) == set(SAMPLE_ARGS), (set(active)-set(SAMPLE_ARGS), set(SAMPLE_ARGS)-set(active))

    descriptions = {}
    checkers = {}
    for iid in active:
        obj = registry.INSTRUCTION_DICT[iid](iid)
        descriptions[iid] = obj.build_description(**SAMPLE_ARGS[iid])
        checkers[iid] = obj

    conflicts = {k:set(v) for k,v in registry.INSTRUCTION_CONFLICTS.items()}

    compatible_pairs = 0
    tested_orientations = 0
    full_pass = 0
    blocked = []
    invalid = []
    exceptions = []

    for i, a in enumerate(active):
        for b in active[i+1:]:
            if b in conflicts.get(a,set()) or a in conflicts.get(b,set()):
                continue
            compatible_pairs += 1

            for order in ((a,b),(b,a)):
                tested_orientations += 1
                # This is a valid synthetic public contract: two rendered checker
                # descriptions and a visible base request. For repeat_prompt the
                # pinned checker is explicitly instantiated with BASE_REQUEST.
                prompt = BASE_REQUEST + "\n" + descriptions[order[0]] + "\n" + descriptions[order[1]]

                try:
                    out = solver.synthesize(prompt)
                except Exception as exc:
                    exceptions.append({
                        "pair":[a,b],
                        "order":list(order),
                        "type":type(exc).__name__,
                        "message":str(exc)[:300],
                    })
                    continue

                if not str(out.get("status","")).startswith("CANDIDATE_PASS"):
                    blocked.append({
                        "pair":[a,b],
                        "order":list(order),
                        "status":out.get("status"),
                        "reason":out.get("reason"),
                        "recognized":out.get("recognized_instruction_ids"),
                    })
                    continue

                response = str(out.get("response") or "")
                verdicts = {}
                try:
                    verdicts[a] = bool(checkers[a].check_following(response))
                    verdicts[b] = bool(checkers[b].check_following(response))
                except Exception as exc:
                    exceptions.append({
                        "pair":[a,b],
                        "order":list(order),
                        "type":type(exc).__name__,
                        "message":str(exc)[:300],
                        "response_prefix":response[:240],
                    })
                    continue

                if verdicts[a] and verdicts[b]:
                    full_pass += 1
                else:
                    invalid.append({
                        "pair":[a,b],
                        "order":list(order),
                        "verdicts":verdicts,
                        "recognized":out.get("recognized_instruction_ids"),
                        "dominant_shape":out.get("dominant_shape"),
                        "response_prefix":response[:400],
                    })

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_PAIR_CONJUNCTION_AUDIT_V1",
        "candidate":{
            "brain_commit":BRAIN_COMMIT,
            "solver_blob":SOLVER_BLOB,
            "inverter_blob":INVERTER_BLOB,
        },
        "upstream":{
            "livebench_commit":LIVEBENCH_COMMIT,
            "blobs":observed,
            "active_types":len(active),
        },
        "compatible_unordered_pairs":compatible_pairs,
        "tested_pair_orientations":tested_orientations,
        "full_exact_checker_pass_orientations":full_pass,
        "blocked_orientations":len(blocked),
        "invalid_witness_orientations":len(invalid),
        "exception_orientations":len(exceptions),
        "blocked_examples":blocked[:25],
        "invalid_examples":invalid[:25],
        "exception_examples":exceptions[:25],
        "terminal_livebench_rows_read":0,
        "terminal_hidden_kwargs_read":0,
        "models_used":0,
        "incremental_spend_usd":0,
    }

    pathlib.Path("livebench_legacy_pair_conjunction_receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))

    # A load-bearing all-pair conjunction claim requires every compatible pair
    # in both visible description orders to produce a witness accepted by both
    # exact pinned checkers.
    if blocked or invalid or exceptions:
        raise SystemExit(1)
    print("LIVEBENCH_LEGACY_PAIR_CONJUNCTION_EXHAUSTIVE_VERIFICATION=PASS")
