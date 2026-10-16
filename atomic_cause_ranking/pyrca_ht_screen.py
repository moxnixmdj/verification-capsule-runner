import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from pyrca.analyzers.ht import HT, HTConfig

SEED = 202610010843
TRIALS = 120
NORMAL_N = 500
ABNORMAL_N = 80
SHIFT = 6.0

rng = np.random.default_rng(SEED)
py_rng = random.Random(SEED)


def make_dag(n: int):
    names = [f"N{i}" for i in range(n)]
    adj = pd.DataFrame(np.zeros((n, n), dtype=int), index=names, columns=names)
    # Guarantee one full backbone so every non-root has ancestors.
    for i in range(n - 1):
        adj.iloc[i, i + 1] = 1
    # Add forward skip edges only, preserving DAG.
    for i in range(n):
        for j in range(i + 2, n):
            if py_rng.random() < 0.22:
                adj.iloc[i, j] = 1
    return names, adj


def parents_of(adj, node):
    return [p for p in adj.index if int(adj.loc[p, node]) != 0]


def descendants_of(adj, source):
    out = set()
    frontier = [source]
    while frontier:
        cur = frontier.pop()
        for child in adj.columns:
            if int(adj.loc[cur, child]) != 0 and child not in out:
                out.add(child)
                frontier.append(child)
    return out


def ancestors_of(adj, target):
    out = set()
    frontier = [target]
    while frontier:
        cur = frontier.pop()
        for parent in adj.index:
            if int(adj.loc[parent, cur]) != 0 and parent not in out:
                out.add(parent)
                frontier.append(parent)
    return out


def simulate(adj, n_rows, intervention_node=None, shift=0.0):
    cols = list(adj.columns)
    data = pd.DataFrame(index=range(n_rows), columns=cols, dtype=float)
    weights = {}
    for i, src in enumerate(cols):
        for j, dst in enumerate(cols):
            if int(adj.loc[src, dst]) != 0:
                # Stable, positive coefficients avoid cancellation.
                weights[(src, dst)] = 0.55 + 0.1 * ((i + j) % 4)

    for node in cols:
        ps = parents_of(adj, node)
        noise = rng.normal(0.0, 1.0, size=n_rows)
        value = noise.copy()
        for p in ps:
            value += weights[(p, node)] * data[p].to_numpy(dtype=float)
        if node == intervention_node:
            value += shift
        data[node] = value
    return data


rows = []
ht_hits = 0
rootmost_hits = 0
closest_hits = 0
usable = 0

for trial in range(TRIALS):
    n = py_rng.randint(5, 9)
    names, adj = make_dag(n)
    target = names[-1]

    candidates = sorted(ancestors_of(adj, target), key=lambda x: int(x[1:]))
    # Require multiple surviving candidates and avoid the target itself.
    if len(candidates) < 3:
        continue

    # Hide the injected root cause from the scorer. Sample across ancestor depths.
    true_cause = py_rng.choice(candidates)

    normal = simulate(adj, NORMAL_N)
    abnormal = simulate(adj, ABNORMAL_N, intervention_node=true_cause, shift=SHIFT)

    model = HT(HTConfig(graph=adj, aggregator="max", root_cause_top_k=len(names)))
    model.train(normal)
    result = model.find_root_causes(abnormal, anomalous_metrics=target, adjustment=False)
    scored = [(node, float(score)) for node, score in result.root_cause_nodes if node in candidates]
    if not scored:
        continue

    ranked = [node for node, _ in sorted(scored, key=lambda x: x[1], reverse=True)]
    ht_top1 = ranked[0]

    # Two trivial graph-order baselines.
    rootmost = min(candidates, key=lambda x: int(x[1:]))
    closest = max(candidates, key=lambda x: int(x[1:]))

    usable += 1
    ht_hits += int(ht_top1 == true_cause)
    rootmost_hits += int(rootmost == true_cause)
    closest_hits += int(closest == true_cause)

    rows.append({
        "trial": trial,
        "nodes": n,
        "target": target,
        "candidate_count": len(candidates),
        "true_cause": true_cause,
        "ht_top1": ht_top1,
        "ht_hit": ht_top1 == true_cause,
        "rootmost": rootmost,
        "rootmost_hit": rootmost == true_cause,
        "closest": closest,
        "closest_hit": closest == true_cause,
        "ht_ranked_candidates": ranked,
    })

if usable < 80:
    raise SystemExit(f"insufficient usable trials: {usable}")

ht_acc = ht_hits / usable
root_acc = rootmost_hits / usable
closest_acc = closest_hits / usable
best_baseline = max(root_acc, closest_acc)
delta = ht_acc - best_baseline

result = {
    "schema": "PROJECT_BRAIN_PYRCA_HT_RESIDUAL_CAUSE_RANKING_SCREEN_V1",
    "status": "SCREEN_ONLY__ZERO_CAPABILITY_CREDIT",
    "seed": SEED,
    "generated_trials": TRIALS,
    "usable_multi_survivor_trials": usable,
    "normal_samples_per_trial": NORMAL_N,
    "abnormal_samples_per_trial": ABNORMAL_N,
    "intervention_shift": SHIFT,
    "candidate_contract": "EXPLICIT_DAG_ANCESTORS_OF_TARGET__MULTIPLE_SURVIVORS",
    "hidden_true_cause_generation": "UNIFORM_RANDOM_ANCESTOR_INTERVENTION",
    "pyrca": {
        "repo": "salesforce/PyRCA",
        "revision": "411310d589fac5cb8e7bdce67d33eadb091a1083",
        "license": "BSD-3-Clause",
        "algorithm": "HT"
    },
    "metrics": {
        "pyrca_ht_top1_accuracy": ht_acc,
        "rootmost_baseline_top1_accuracy": root_acc,
        "closest_to_target_baseline_top1_accuracy": closest_acc,
        "delta_vs_best_graph_order_baseline": delta
    },
    "screen_gate": {
        "min_usable_trials": 80,
        "min_ht_top1_accuracy": 0.70,
        "min_delta_vs_best_graph_order_baseline": 0.25,
        "pass": usable >= 80 and ht_acc >= 0.70 and delta >= 0.25
    },
    "interpretation_rule": "PASS_ONLY_SUPPORTS_PYRCA_HT_AS_A_RESIDUAL_CAUSE_RANKING_CHALLENGER_ON_EXPLICIT_NUMERIC_CAUSAL_DAGS_WITH_MULTIPLE_SURVIVORS__NO_EDGE_DISCOVERY_GENERAL_RCA_OR_FAMILY_CREDIT",
    "rows": rows,
    "capability_credit_delta": 0
}

out = Path("atomic_cause_ranking/pyrca_ht_result.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))

if not result["screen_gate"]["pass"]:
    raise SystemExit(1)
