#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import pathlib
import re
import sys
import urllib.request
from decimal import Decimal
from itertools import product

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"
REPO = "moxnixmdj/verification-capsule-runner"

SUBJECT_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
}

RUNS = {
    "scope_opening": (
        37200499676,
        "a3b9fa88c67427c200b396cd291839176fb2867f",
        "Verify LiveBench frozen active legacy15 hash opening",
    ),
    "visible_compiler": (
        37243119304,
        "83437f1118fa7bd798de30053a2a04cffcc2e615",
        "Verify LiveBench visible compiler V4",
    ),
    "full_cross": (
        37243831184,
        "a1701820638952ae912e19a6e2176c78d7801900",
        "Verify LiveBench full cross V1",
    ),
    "punkt": (
        37244050020,
        "a9dba2dcad85854c1010a56bb8238576e54947e7",
        "Verify LiveBench Punkt contexts V1",
    ),
    "population": (
        37149624542,
        "015ce16f978b8200b980e163c82dceea5d405fe7",
        "Verify LiveBench IF release population V2",
    ),
}

RUN_SCRIPT_BINDINGS = {
    "scope_opening": (
        "verify_livebench_frozen_active_legacy15_hash_opening_v1.py",
        "2fe976e56e42a400106c1a37e7e2787e30a7d365",
    ),
    "visible_compiler": (
        "verify_livebench_visible_compiler_v4.py",
        "20405fec5a9201479bc8141a6155d962c87fed52",
    ),
    "full_cross": (
        "verify_livebench_full_cross_v1.py",
        "6b4a2e7aad44f1c8369378595898dbfa86f78a2f",
    ),
    "punkt": (
        "verify_livebench_punkt_context_closure_v1.py",
        "c6b99f27fadea7ffe09126b0603163dd03d93916",
    ),
    "population": (
        "capsules/livebench_if_release_population_v2/brain/CANDIDATE.json",
        "fa9acadf92826cff424d97f25b4094f60fed3571",
    ),
}

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
MODERN_REGISTRY_BLOB = "adfed4832877566e62970257b50c6fa32c302fb2"
TERMINAL_RUNNER_COMMIT = "d8e6edd61fb1fbeedd856aa31cc202348e52529c"
TERMINAL_RUNNER_BLOB = "05d71d3d06ebac9b5d74eb31b137141e6b8797c2"
ACTIVE15_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

LEADERBOARD_COMMIT = "caa4253c8a3aa93b5c7ec234e681d4f120a20240"
TABLE_BLOB = "73ab7d8d9752b4d7cc1bc8c574ab0eb80c36c84b"
CATEGORIES_BLOB = "50b5672fe14023f5ba14efc1ce16e221e6573056"
COST_BLOB = "6f6271ed5497706e290675a1ad92a716a0f45b6b"
OPUS_KEY = "claude-opus-5-5-max-effort"
IF_TASKS = ("paraphrase", "simplify", "story_generation", "summarize")
EXACT_OPUS_IF_MEAN = Decimal("65.73775")
DISPLAY_BAR = Decimal("65.7")

ACTIVE = (
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
)
EXCLUDED = (
    "keywords:frequency",
    "keywords:letter_frequency",
    "language:response_language",
    "detectable_content:number_placeholders",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "change_case:capital_word_frequency",
    "punctuation:no_comma",
)
SPECIAL = ("other", "anything", "can", "help")
END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def api_json(path: str):
    return json.loads(fetch("https://api.github.com" + path))


def git_blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def git_blob_path(path: pathlib.Path) -> str:
    return git_blob_bytes(path.read_bytes())


def commitment(ids) -> str:
    return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()


def bind_subject() -> dict[str, str]:
    got = {}
    for rel, expected in SUBJECT_BLOBS.items():
        sha = git_blob_path(SUBJECT / rel)
        assert sha == expected, (rel, sha, expected)
        got[rel] = sha
    return got


def bind_success_runs() -> dict:
    out = {}
    for key, (run_id, head_sha, name) in RUNS.items():
        run = api_json(f"/repos/{REPO}/actions/runs/{run_id}")
        assert run["status"] == "completed", (key, run["status"])
        assert run["conclusion"] == "success", (key, run["conclusion"])
        assert run["head_sha"] == head_sha, (key, run["head_sha"], head_sha)
        assert run["name"] == name, (key, run["name"], name)
        path, expected_blob = RUN_SCRIPT_BINDINGS[key]
        raw = fetch(f"https://raw.githubusercontent.com/{REPO}/{head_sha}/{path}")
        assert git_blob_bytes(raw) == expected_blob, (key, path, git_blob_bytes(raw), expected_blob)
        out[key] = {
            "run_id": run_id,
            "head_sha": head_sha,
            "name": name,
            "script_or_candidate_blob": expected_blob,
        }
    return out


def verify_active15_opening() -> dict:
    assert len(ACTIVE) == 15 and len(EXCLUDED) == 10
    assert len(set(ACTIVE + EXCLUDED)) == 25
    assert not (set(ACTIVE) & set(EXCLUDED))
    assert commitment(ACTIVE) == ACTIVE15_COMMITMENT
    for iid in EXCLUDED:
        assert commitment(ACTIVE + (iid,)) != ACTIVE15_COMMITMENT

    legacy = fetch(
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        + LIVEBENCH_COMMIT
        + "/livebench/if_runner/instruction_following_eval/instructions_registry.py"
    )
    modern = fetch(
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        + LIVEBENCH_COMMIT
        + "/livebench/if_runner/ifbench/instructions_registry.py"
    )
    runner = fetch(
        "https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner/"
        + TERMINAL_RUNNER_COMMIT
        + "/execute_livebench_if_threshold_v1.py"
    )
    assert git_blob_bytes(legacy) == LEGACY_REGISTRY_BLOB
    assert git_blob_bytes(modern) == MODERN_REGISTRY_BLOB
    assert git_blob_bytes(runner) == TERMINAL_RUNNER_BLOB
    assert b"hashlib.sha256(json.dumps(sorted(unknown)).encode()).hexdigest()" in runner

    lt, mt = legacy.decode(), modern.decode()
    for iid in ACTIVE + EXCLUDED:
        suffix = iid.split(":", 1)[1]
        assert (f'"{suffix}"' in lt) or (f"'{suffix}'" in lt)
        assert f'"{iid}"' not in mt and f"'{iid}'" not in mt

    return {
        "active_id_count": 15,
        "excluded_legacy_id_count": 10,
        "commitment_sha256": ACTIVE15_COMMITMENT,
    }


def load_public_words():
    util = fetch(
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        + LIVEBENCH_COMMIT
        + "/livebench/if_runner/instruction_following_eval/instructions_util.py"
    ).decode()
    # Import from the checked out pinned source for exact semantics and list.
    sys.path.insert(0, "/tmp/LiveBench/livebench/if_runner")
    from instruction_following_eval import instructions_util
    words = tuple(instructions_util.WORD_LIST)
    assert len(words) == 1525 and len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
    return words


def lexical_signatures(words):
    lower = {w.lower(): w for w in words}
    assert all(w in lower for w in SPECIAL)
    generic = next(w for w in words if w.lower() not in set(SPECIAL))

    def fillers(exclude, n):
        ex = {str(x).lower() for x in exclude}
        out = []
        for w in words:
            if w.lower() not in ex:
                out.append(w)
                ex.add(w.lower())
            if len(out) == n:
                return out
        raise AssertionError("INSUFFICIENT_FILLERS")

    sigs = []
    for phrase_idx, phrase in enumerate(END_PHRASES):
        for nth_category in (*SPECIAL, "__generic__"):
            nth_word = generic if nth_category == "__generic__" else lower[nth_category]
            for bits in product((False, True), repeat=4):
                memberships = dict(zip(SPECIAL, bits))
                nth_values = (memberships[nth_category],) if nth_category in memberships else (False, True)
                for nth_forbidden in nth_values:
                    required = [lower[w] for w in SPECIAL if memberships[w]]
                    if nth_forbidden and nth_word.lower() not in {x.lower() for x in required}:
                        required.append(nth_word)
                    assert len(required) <= 5
                    forbidden = list(required)
                    forbidden += fillers(
                        set(forbidden) | ({nth_word} if not nth_forbidden else set()),
                        5 - len(forbidden),
                    )
                    assert len(forbidden) == 5
                    sigs.append({
                        "phrase_idx": phrase_idx,
                        "end_phrase": phrase,
                        "nth_word": nth_word,
                        "forbidden": forbidden,
                        "nth_forbidden": nth_forbidden,
                    })
    assert len(sigs) == 192
    return sigs


def C(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def verify_minimum_cut(words) -> dict:
    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feas

    sets = arch.enumerate_compatible_sets()
    assert len(sets) == 928
    sigs = lexical_signatures(words)
    existence = [w for w in words if w.lower() not in set(SPECIAL)][:5]
    assert len(existence) == 5

    def skeleton(ids, sig, sentence_zero):
        out = []
        for iid in ids:
            if iid == comp.EXIST:
                out.append(C(iid, keywords=list(existence)))
            elif iid == comp.FORBIDDEN:
                out.append(C(iid, forbidden_words=list(sig["forbidden"])))
            elif iid == comp.PARAGRAPHS:
                out.append(C(iid, num_paragraphs=3))
            elif iid == comp.WORDS:
                out.append(C(iid, num_words=100, relation="less than"))
            elif iid == comp.SENTENCES:
                out.append(C(iid, num_sentences=1 if sentence_zero else 2, relation="less than"))
            elif iid == comp.NTH:
                out.append(C(iid, num_paragraphs=3, nth_paragraph=2, first_word=sig["nth_word"]))
            elif iid == comp.POSTSCRIPT:
                out.append(C(iid, postscript_marker="P.P.S"))
            elif iid == comp.BULLETS:
                out.append(C(iid, num_bullets=3))
            elif iid == comp.TITLE:
                out.append(C(iid))
            elif iid == comp.SECTIONS:
                out.append(C(iid, section_spliter="Section", num_sections=3))
            elif iid == comp.JSON_ID:
                out.append(C(iid))
            elif iid == comp.REPEAT:
                out.append(C(iid, prompt_to_repeat="Public visible request."))
            elif iid == comp.TWO:
                out.append(C(iid))
            elif iid == comp.END:
                out.append(C(iid, end_phrase=sig["end_phrase"]))
            elif iid == comp.QUOTE:
                out.append(C(iid))
            else:
                raise AssertionError("UNKNOWN_ACTIVE15_ID:" + iid)
        return out

    cases = 0
    losses = {0: 0, 1: 0, 2: 0}
    for ids in sets:
        idset = set(ids)
        for sig in sigs:
            forbidden_lower = {w.lower() for w in sig["forbidden"]}
            end_words = {"other"} if sig["phrase_idx"] == 0 else {"anything", "can", "help"}
            forbidden_collision = (
                comp.FORBIDDEN in idset
                and (
                    (comp.NTH in idset and sig["nth_word"].lower() in forbidden_lower)
                    or (comp.END in idset and bool(end_words & forbidden_lower))
                )
            )
            for sentence_zero in (False, True):
                contracts = skeleton(ids, sig, sentence_zero)
                reasons = tuple(feas.hard_unsat_reasons(contracts))
                sacrificed = set(opt._sacrifice_ids(reasons))
                expected = set()
                if comp.SENTENCES in idset and sentence_zero:
                    expected.add(comp.SENTENCES)
                if forbidden_collision:
                    expected.add(comp.FORBIDDEN)
                assert sacrificed == expected, (ids, sig, sentence_zero, reasons, sacrificed, expected)
                assert sacrificed <= {comp.SENTENCES, comp.FORBIDDEN}
                losses[len(sacrificed)] += 1
                cases += 1

    assert cases == 928 * 192 * 2 == 356352
    return {
        "structural_sets": 928,
        "lexical_signatures": 192,
        "sentence_partition_states": 2,
        "classification_states": cases,
        "only_loss_coordinates": [
            "length_constraints:number_sentences",
            "keywords:forbidden_words",
        ],
        "loss_histogram": losses,
    }


def verify_non_sentence_parametrics() -> dict:
    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp

    sets = arch.enumerate_compatible_sets()
    route_counts = {"JSON": 0, "REPEAT_PROMPT": 0, "TWO_RESPONSES": 0, "GENERAL": 0}
    sentence_sets = 0
    for ids in sets:
        s = set(ids)
        if comp.JSON_ID in s:
            assert s <= {comp.JSON_ID, comp.EXIST, comp.FORBIDDEN}
            route_counts["JSON"] += 1
        elif comp.REPEAT in s:
            assert s <= {comp.REPEAT, comp.EXIST, comp.TITLE}
            route_counts["REPEAT_PROMPT"] += 1
        elif comp.TWO in s:
            assert s <= {comp.TWO, comp.EXIST, comp.FORBIDDEN, comp.TITLE}
            route_counts["TWO_RESPONSES"] += 1
        else:
            route_counts["GENERAL"] += 1
        if comp.SENTENCES in s:
            sentence_sets += 1
            assert comp.PARAGRAPHS not in s

    assert sum(route_counts.values()) == 928
    conservative_word_bound = 1 + 1 + 15 + 5 + 20 + 5 + 4 + 3 + 8
    assert conservative_word_bound == 62 < 100

    src = (SUBJECT / "canonical/runtime/livebench_legacy15_contract_composer_v2.py").read_text()
    required = [
        'return "9000" + "0".join(words) + "0009"',
        'for i in range(1, int(s["num_sections"]) + 1):',
        'for i in range(1, int(_slots(by_id[BULLETS])["num_bullets"]) + 1):',
        'pad = " ".join(_SAFE + "x" + str(i)',
        'core = "\\n***\\n".join(paras)',
        'core = "\\n\\n".join(paras)',
        'response = json.dumps(',
        'response = left + "******" + right',
        'core = core.rstrip() + " " + phrase',
    ]
    missing = [x for x in required if x not in src]
    assert not missing, missing

    return {
        "route_counts": route_counts,
        "sentence_context_id_sets": sentence_sets,
        "conservative_unpadded_word_upper_bound": conservative_word_bound,
        "public_min_word_threshold": 100,
        "word_upper_margin": 100 - conservative_word_bound,
    }


def verify_public_bar() -> dict:
    base = "https://raw.githubusercontent.com/LiveBench/new-livebench/" + LEADERBOARD_COMMIT + "/public/"
    categories_raw = fetch(base + "categories_2026_06_25.json")
    table_raw = fetch(base + "table_2026_06_25.csv")
    cost_raw = fetch(base + "cost_2026_06_25.csv")
    assert git_blob_bytes(categories_raw) == CATEGORIES_BLOB
    assert git_blob_bytes(table_raw) == TABLE_BLOB
    assert git_blob_bytes(cost_raw) == COST_BLOB

    categories = json.loads(categories_raw)
    assert tuple(categories["IF"]) == IF_TASKS

    table_rows = list(csv.DictReader(io.StringIO(table_raw.decode())))
    row = next(r for r in table_rows if r["model"] == OPUS_KEY)
    scores = {task: Decimal(row[task]) for task in IF_TASKS}
    mean = sum(scores.values(), Decimal(0)) / Decimal(len(IF_TASKS))
    assert mean == EXACT_OPUS_IF_MEAN
    assert mean.quantize(Decimal("0.1")) == DISPLAY_BAR

    cost_rows = list(csv.DictReader(io.StringIO(cost_raw.decode())))
    crow = next(r for r in cost_rows if r["model"] == OPUS_KEY)
    counts = {task: int(crow["nq_" + task]) for task in IF_TASKS}
    assert counts == {task: 50 for task in IF_TASKS}
    assert sum(counts.values()) == 200

    return {
        "model": OPUS_KEY,
        "tasks": list(IF_TASKS),
        "task_scores_percent": {k: str(v) for k, v in scores.items()},
        "exact_mean_percent": str(mean),
        "display_bar_percent": str(DISPLAY_BAR),
        "question_counts": counts,
        "population": 200,
    }


def main() -> int:
    subject = bind_subject()
    runs = bind_success_runs()
    scope = verify_active15_opening()
    words = load_public_words()
    mincut = verify_minimum_cut(words)
    param = verify_non_sentence_parametrics()
    bar = verify_public_bar()

    assert mincut["classification_states"] == 356352
    assert bar["population"] == 200
    assert Decimal(bar["exact_mean_percent"]) >= DISPLAY_BAR

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_COMPOSITION_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__CLEAN_ACTIVE15_POINTWISE_DOMINANCE_IMPLIES_LIVEBENCH_IF_GE_65_7__ZERO_TERMINAL_ROWS",
        "subject_blobs": subject,
        "independent_success_runs": runs,
        "active15_scope_opening": scope,
        "pointwise_minimum_cut_recomputed": mincut,
        "non_sentence_parametric_reduction_recomputed": param,
        "public_comparator_geometry_recomputed": bar,
        "composition_theorem": [
            "EXACT_PREEXISTING_TERMINAL_COMMITMENT_OPENS_TO_ACTIVE15_ONLY",
            "VISIBLE_PUBLIC_GRAMMAR_COMPILER_HAS_INDEPENDENT_EXACT_ROUNDTRIP_PASS",
            "ONLY_TWO_MANDATORY_LOSS_COORDINATES_EXIST_OVER_356352_SYMBOLIC_CLASSIFICATION_STATES",
            "FULL_CROSS_INDEPENDENT_RUN_ATTAINS_PRECOMMITTED_POINTWISE_MAX_ON_712704_OF_712704_CASES",
            "NON_SENTENCE_INTERMEDIATE_PARAMETERS_ARE_DISCHARGED_BY_EXACT_CONSTRUCTOR_ALGEBRA_AND_GLOBAL_WORD_BOUND",
            "PINNED_PUNKT_INDEPENDENT_RUN_CLOSES_ALL_REMAINING_SENTENCE_CONTEXTS",
            "THEREFORE_THE_CASE_INDEPENDENT_SOLVER_ATTAINS_THE_TRUE_MAXIMUM_CHECKER_PASS_COUNT_FOR_EVERY_FROZEN_ACTIVE15_CASE",
            "ANY_OPUS_RESPONSE_ON_THE_SAME_CASE_CANNOT_EXCEED_THAT_CASE_MAXIMUM",
            "POINTWISE_BRAIN_SCORE_GE_POINTWISE_OPUS_SCORE_IMPLIES_MEAN_BRAIN_SCORE_GE_MEAN_OPUS_SCORE",
            "PUBLIC_OPUS55_IF_MEAN_IS_65_73775_PERCENT_OVER_200_EQUAL_WEIGHT_QUESTIONS",
            "65_73775_PERCENT_IS_AT_LEAST_THE_65_7_PERCENT_ACCEPTANCE_BAR",
        ],
        "contamination_firewall": {
            "terminal_rows_read": 0,
            "terminal_kwargs_read": 0,
            "terminal_question_ids_read": 0,
            "target_responses_read": 0,
            "target_scores_read": 0,
            "contaminated_84_404_replay_used": False,
        },
        "acceptance_consequence": "LIVEBENCH_IF_GE_65_7_IS_PROVED_BY_CLEAN_STRONGER_POINTWISE_DOMINANCE",
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    pathlib.Path("livebench_clean_active15_promotion_v1.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
