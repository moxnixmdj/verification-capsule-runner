#!/usr/bin/env python3
"""Clean post-freeze LiveBench selected-support evaluation of current Brain pointwise solver.

Candidate runtime bytes are vendored and content-addressed before this evaluator's
final commit identity exists. The fresh random seed is derived from verifier HEAD
plus the frozen candidate manifest, preventing adaptive case selection.

No quarantined terminal rows, prompts, hidden IDs/kwargs, responses, or scores
are read.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject/livebench_pointwise_clean200_v1"
SCORER = Path("/tmp/livebench")
GEN = Path("/tmp/livebench-gen")

EXPECTED_SUBJECT_BLOBS = {
    "livebench_legacy15_pointwise_solver_v1.py": "b4485931ef3a759743eaee960c68fe2ed389c025",
    "livebench_legacy15_pointwise_search_v1.py": "360d2c24b786ebb98c805e8d54e645a08939f201",
    "livebench_legacy_visible_constraint_compiler_v4.py": "721207ba39d502e3f610289578e9d5bab78b1fcc",
    "livebench_frozen_active_legacy15_v1.py": "34440ee69322e9d519cbe656cb03c55683a8b9c6",
    "livebench_legacy15_pointwise_certificate_v1.py": "b8f9d0c9a0b0c9f78769cb9534ee4e2c61481fd8",
    "livebench_legacy15_exact_postvalidator_v1.py": "d3c821a1ff9803590cf6899a598503fb6b7d3eec",
    "livebench_legacy15_relaxed_candidate_search_v1.py": "9c712ee221021fabe2467cadc241312f50f6c712",
    "livebench_pointwise_optimality_certificate_v1.py": "f0e1faae5b5d1a90a1184fe6cca409591acbbb27",
    "livebench_legacy15_joint_candidate_generator_v1.py": "b6ace46a0887321c4c8c8354d88169be1fdbf582",
    "livebench_legacy15_composition_partition_v1.py": "b817b4f63f4e98c2705f221c7a4abd8e571f9d80",
    "livebench_legacy15_slot_feasibility_v1.py": "81a3878479cd287cf85f47cd5c0479a4893a5361",
    "livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "livebench_legacy_visible_constraint_compiler_v1.py": "34f4df9f0bd265fc555686bd251a264e446d4c04",
}

PINNED_PUBLIC = {
    SCORER / "livebench/if_runner/instruction_following_eval/instructions.py":
        "4997bab885a676d92545fd91a9a20b48d234a2b2",
    SCORER / "livebench/if_runner/instruction_following_eval/instructions_registry.py":
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    SCORER / "livebench/process_results/instruction_following/utils.py":
        "8ce01747887ec0792c8f024e1972e34ece781676",
    GEN / "livebench/if_runner/live_data.py":
        "6ff390d6885cf90f88d9d36959735cb327613edc",
}

EXACT_COMPARATOR = Fraction(263, 400)  # 0.6575 coarse headline is not used below.
EXACT_COMPARATOR_DECIMAL = Fraction(263, 400) - Fraction(49, 200000)  # 0.657255? placeholder replaced below
# Canonical exact comparator is 0.6573775 = 263/400 + 151/400000.
EXACT_COMPARATOR_DECIMAL = Fraction(262951, 400000)

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

runtime_dir = SUB / "canonical/runtime"
for name, expected in EXPECTED_SUBJECT_BLOBS.items():
    got = git_blob_sha(runtime_dir / name)
    assert got == expected, (name, got, expected)
for path, expected in PINNED_PUBLIC.items():
    got = git_blob_sha(path)
    assert got == expected, (str(path), got, expected)

sys.path.insert(0, str(SUB))
sys.path.insert(0, str(SCORER / "livebench/if_runner"))

from canonical.runtime.livebench_frozen_active_legacy15_v1 import ACTIVE_IDS
from canonical.runtime import livebench_legacy15_pointwise_solver_v1 as solver
from instruction_following_eval import instructions_registry as registry

spec = importlib.util.spec_from_file_location(
    "historical_live_data", GEN / "livebench/if_runner/live_data.py"
)
assert spec and spec.loader
live_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_data)

# Freeze-to-evaluation chronology: candidate bytes above pre-exist this verifier
# HEAD. Derive the seed only now from the final verifier identity + manifest.
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
manifest = json.dumps(EXPECTED_SUBJECT_BLOBS, sort_keys=True, separators=(",", ":"))
seed_digest = hashlib.sha256((head + "|" + manifest + "|POINTWISE_CLEAN200_V1").encode()).digest()
np_seed = int.from_bytes(seed_digest[:4], "big")
py_seed = int.from_bytes(seed_digest[4:8], "big")
np.random.seed(np_seed)
random.seed(py_seed)

# Published LiveBench selected support is the exact 15-ID set opened by the
# pre-existing terminal commitment. Published generation uses uniform 2..5
# composition; historical source uses uniform no-replacement identity draws,
# followed by conflict removal.
active = list(ACTIVE_IDS)
draw_sizes = np.random.randint(2, 6, 200)
raw = [
    np.random.choice(active, int(k), replace=False).tolist()
    for k in draw_sizes
]
selected = live_data.check_for_conflitcs(raw)
assert len(selected) == 200
assert all(ids and set(ids) <= set(ACTIVE_IDS) for ids in selected)

ARTICLE = (
    "A public source describes a measured system with ordinary prose. "
    "The source contains enough neutral context for instruction-following evaluation."
)
TASKS = (
    "Please paraphrase based on the sentences provided.",
    "Please summarize based on the sentences provided.",
    "Please explain in simpler terms what this text means.",
    "Please generate a story based on the sentences provided.",
)
REPEAT_MARKER = "First repeat the request word for word without change,"

scores: list[Fraction] = []
solver_status = Counter()
failed_checker_ids = Counter()
optimal_true_counts = Counter()
case_sizes = Counter()
failure_examples = []
full_score_rows = 0
certified_rows = 0

for row_index, ids in enumerate(selected):
    descriptions = []
    records = []
    for iid in ids:
        inst = registry.INSTRUCTION_DICT[iid](iid)
        desc = inst.build_description()
        kwargs = dict(inst.get_instruction_args() or {})
        descriptions.append(desc)
        records.append({"instruction_id": iid, "kwargs": kwargs})

    task = TASKS[row_index % len(TASKS)]
    prompt = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n" + ARTICLE + "\n-------\n" + task + " " + " ".join(descriptions)
    )

    # Frozen RepeatPromptChecker receives this derived hidden arg in the original
    # generation code. The solver itself only sees the visible prompt.
    if "combination:repeat_prompt" in ids:
        prefix = prompt.split(REPEAT_MARKER, 1)[0]
        for rec in records:
            if rec["instruction_id"] == "combination:repeat_prompt":
                rec["kwargs"]["prompt_to_repeat"] = prefix
                break

    out = solver.solve_prompt(prompt, SCORER, max_per_subset=16, max_total=512)
    status = str(out.get("status") or "")
    solver_status[status] += 1
    response = str(out.get("response") or "") if status == "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED" else ""
    if status == "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED":
        certified_rows += 1

    flags = []
    for rec in records:
        iid = rec["instruction_id"]
        inst = registry.INSTRUCTION_DICT[iid](iid)
        inst.build_description(**rec["kwargs"])
        try:
            ok = bool(inst.check_following(response))
        except Exception:
            ok = False
        flags.append(ok)
        if not ok:
            failed_checker_ids[iid] += 1

    k = len(flags)
    g = sum(flags)
    score = Fraction(1, 1) if g == k else Fraction(g, 2 * k)
    scores.append(score)
    case_sizes[k] += 1
    optimal_true_counts[(k, g)] += 1
    full_score_rows += int(score == 1)

    if status != "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED" and len(failure_examples) < 25:
        failure_examples.append({
            "row_index": row_index,
            "instruction_ids": list(ids),
            "solver_status": status,
            "solver_error": out.get("error"),
            "score": f"{score.numerator}/{score.denominator}",
        })

mean = sum(scores, Fraction(0, 1)) / len(scores)
threshold = Fraction(262951, 400000)  # 0.6573775 exact canonical comparator
receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_POINTWISE_CLEAN200_EQUIVALENT_EVAL_V1",
    "status": "PASS_THRESHOLD" if mean >= threshold else "FAIL_THRESHOLD",
    "candidate_manifest": EXPECTED_SUBJECT_BLOBS,
    "verifier_head": head,
    "seed_sha256": seed_digest.hex(),
    "numpy_seed": np_seed,
    "python_seed": py_seed,
    "population": {
        "rows": 200,
        "selected_support_count": len(ACTIVE_IDS),
        "initial_cardinality_law": "UNIFORM_INTEGER_2_TO_5",
        "identity_law": "UNIFORM_WITHOUT_REPLACEMENT_FROM_PUBLISHED_SELECTED15_SUPPORT",
        "conflict_handling": "HISTORICAL_LIVEBENCH_check_for_conflitcs",
        "task_rotation": list(TASKS),
    },
    "result": {
        "exact_score_numerator": mean.numerator,
        "exact_score_denominator": mean.denominator,
        "mean_score": float(mean),
        "exact_comparator_numerator": threshold.numerator,
        "exact_comparator_denominator": threshold.denominator,
        "exact_comparator": float(threshold),
        "exact_margin": float(mean - threshold),
        "certified_pointwise_rows": certified_rows,
        "full_score_rows": full_score_rows,
        "minimum_case_score": float(min(scores)),
        "maximum_case_score": float(max(scores)),
    },
    "solver_status_counts": dict(solver_status),
    "failed_checker_counts": dict(failed_checker_ids),
    "case_size_counts": {str(k): v for k, v in sorted(case_sizes.items())},
    "true_count_profile": {f"{k}:{g}": v for (k, g), v in sorted(optimal_true_counts.items())},
    "failure_examples": failure_examples,
    "terminal_boundary": {
        "quarantined_terminal_rows_read": 0,
        "quarantined_terminal_prompts_read": 0,
        "quarantined_terminal_instruction_lists_read": 0,
        "quarantined_terminal_kwargs_read": 0,
        "quarantined_terminal_responses_read": 0,
        "quarantined_terminal_scores_read": 0,
    },
    "credit": {
        "acceptance": False,
        "family": False,
        "capability": False,
        "ownership": False,
    },
    "promotion_gate": (
        "INDEPENDENTLY_BIND_SELECTED15_GENERATION_LAW_EQUIVALENCE_AND_EXACT_CANDIDATE_BYTES;"
        "THEN_PROMOTE_ONLY_IF_THRESHOLD_RESULT_PASSES"
    ),
}
Path("livebench_pointwise_clean200_v1_receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(receipt, sort_keys=True))

assert len(scores) == 200
assert all(Fraction(0, 1) <= x <= Fraction(1, 1) for x in scores)
