import json
import statistics
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

from RCAEval.graph_construction.pc import pc_default
from RCAEval.io.time_series import preprocess

from brain_owned_ht_ranker import ResidualCauseRanker

DATASET_REPO = "phamquiluan/RCAEval"
RCA_COMMIT = "259ea4167160256a74ad30004aa3d96a998c846e"
PILOT_CASES = 4
WINDOW = 300


def norm_dataset(x):
    return "".join(ch for ch in str(x).lower() if ch.isalnum())


def pick_column(columns, *names):
    lower = {str(c).lower(): c for c in columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    raise KeyError(f"missing required column; tried {names}; got {list(columns)}")


def adj_to_parents(adj, names):
    graph = nx.DiGraph()
    graph.add_nodes_from(names)
    n = len(names)
    for a in range(n):
        for b in range(a + 1, n):
            ab = int(adj[a, b])
            ba = int(adj[b, a])
            if ab == ba == 0:
                continue
            if ab == ba == -1:
                graph.add_edge(names[b], names[a])
            elif ab == 1 and ba == -1:
                graph.add_edge(names[b], names[a])
            elif ab == -1 and ba == 1:
                graph.add_edge(names[a], names[b])
            elif ab == 0 and ba == 1:
                graph.add_edge(names[b], names[a])
            elif ab == 1 and ba == 0:
                graph.add_edge(names[a], names[b])
            else:
                raise ValueError(f"unexpected PC edge encoding {ab},{ba} for {names[a]},{names[b]}")
    graph = graph.reverse(copy=True)
    return {node: list(graph.predecessors(node)) for node in names}, list(graph.edges())


def to_mapping(df):
    return {c: df[c].to_numpy(dtype=float) for c in df.columns}


index_path = hf_hub_download(
    repo_id=DATASET_REPO,
    repo_type="dataset",
    filename="cases.parquet",
)
idx = pd.read_parquet(index_path)
case_col = pick_column(idx.columns, "case")
dataset_col = pick_column(idx.columns, "dataset")
root_col = pick_column(idx.columns, "root_cause_service")
fault_col = pick_column(idx.columns, "fault")
inject_col = pick_column(idx.columns, "inject_time", "injection_time", "fault_injection_time")

subset = idx[
    idx[dataset_col].map(norm_dataset).eq("re1ob")
    & idx[fault_col].astype(str).str.lower().isin(["cpu", "mem"])
].copy()
subset = subset.sort_values(case_col.astype(str) if False else case_col)

chosen = []
seen_services = set()
fault_counts = {"cpu": 0, "mem": 0}
for _, row in subset.iterrows():
    service = str(row[root_col])
    fault = str(row[fault_col]).lower()
    if fault_counts[fault] >= 2:
        continue
    if service in seen_services:
        continue
    chosen.append(row)
    seen_services.add(service)
    fault_counts[fault] += 1
    if len(chosen) >= PILOT_CASES:
        break

if len(chosen) < PILOT_CASES:
    raise RuntimeError(f"could not select {PILOT_CASES} distinct real cases; got {len(chosen)}")

rows = []
for row in chosen:
    case = str(row[case_col])
    root_service = str(row[root_col])
    fault = str(row[fault_col]).lower()
    inject_time = int(row[inject_col])

    metrics_path = hf_hub_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        filename=f"{case}/metrics.parquet",
    )
    raw = pd.read_parquet(metrics_path).sort_values("time")
    if "time.1" in raw.columns:
        raw = raw.drop(columns=["time.1"])
    raw = raw.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)

    normal_raw = raw[raw["time"] < inject_time].tail(WINDOW)
    abnormal_raw = raw[raw["time"] >= inject_time].head(WINDOW)
    if len(normal_raw) < 30 or len(abnormal_raw) < 30:
        raise RuntimeError(f"case {case} has insufficient windows: {len(normal_raw)}, {len(abnormal_raw)}")

    combined_raw = pd.concat([normal_raw, abnormal_raw], ignore_index=True)
    processed = preprocess(combined_raw.copy(), dataset="re1-ob", dk_select_useful=False)
    processed = processed.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)

    normal = processed.iloc[: len(normal_raw)].copy()
    abnormal = processed.iloc[len(normal_raw) :].copy()

    # PC is deliberately an external graph supplier. This experiment makes no
    # graph-discovery ownership claim.
    adj = pc_default(processed, show_progress=False, with_bg=False)
    names = list(processed.columns)
    parents, edges = adj_to_parents(adj, names)

    owned = ResidualCauseRanker(names, parents).fit(to_mapping(normal))
    ranking = owned.rank(to_mapping(abnormal))
    ranked_names = [n for n, _ in ranking]

    root_metric = f"{root_service}_{fault}"
    metric_rank = ranked_names.index(root_metric) + 1 if root_metric in ranked_names else None
    service_ranks = [
        i + 1 for i, name in enumerate(ranked_names)
        if name.split("_", 1)[0].replace("-db", "") == root_service.replace("-db", "")
    ]
    service_rank = min(service_ranks) if service_ranks else None

    rows.append({
        "case": case,
        "root_cause_service": root_service,
        "fault": fault,
        "inject_time": inject_time,
        "metric_count": len(names),
        "pc_edge_count": len(edges),
        "root_metric": root_metric,
        "root_metric_rank": metric_rank,
        "root_service_best_metric_rank": service_rank,
        "top10": ranked_names[:10],
    })

service_top3 = sum(r["root_service_best_metric_rank"] is not None and r["root_service_best_metric_rank"] <= 3 for r in rows)
service_top5 = sum(r["root_service_best_metric_rank"] is not None and r["root_service_best_metric_rank"] <= 5 for r in rows)
metric_top10 = sum(r["root_metric_rank"] is not None and r["root_metric_rank"] <= 10 for r in rows)
service_ranks = [r["root_service_best_metric_rank"] for r in rows if r["root_service_best_metric_rank"] is not None]

result = {
    "schema": "PROJECT_BRAIN_RCA_REAL_TRACE_TRANSFER_PILOT_V1",
    "status": "REAL_TRACE_PILOT__ZERO_FAMILY_CREDIT",
    "dataset": {
        "repo": DATASET_REPO,
        "rcaeval_code_revision": RCA_COMMIT,
        "suite": "RE1-OB",
        "cases": len(rows),
        "faults": ["cpu", "mem"],
        "ground_truth_source": "RCAEval cases.parquet annotations",
    },
    "graph_supplier": {
        "implementation": "RCAEval.graph_construction.pc.pc_default",
        "ownership_claim": False,
        "purpose": "SUPPLIED_GRAPH_FOR_RANKING_TRANSFER_ONLY",
    },
    "brain_ranker": {
        "implementation": "brain_owned_ht_ranker.ResidualCauseRanker",
        "canonical_blob": "18edb083ab52d845fefe757df5a300cdd07b33f7",
        "external_ranker_donor_required": False,
    },
    "metrics": {
        "root_service_top3_fraction": service_top3 / len(rows),
        "root_service_top5_fraction": service_top5 / len(rows),
        "root_metric_top10_fraction": metric_top10 / len(rows),
        "median_root_service_best_metric_rank": statistics.median(service_ranks) if service_ranks else None,
    },
    "pilot_gate": {
        "min_root_service_top3_fraction": 0.5,
        "min_root_service_top5_fraction": 0.75,
        "min_root_metric_top10_fraction": 0.5,
        "pass": (
            service_top3 / len(rows) >= 0.5
            and service_top5 / len(rows) >= 0.75
            and metric_top10 / len(rows) >= 0.5
        ),
    },
    "interpretation_rule": "PASS_SUPPORTS_ONLY_FRESH_REAL_TELEMETRY_TRANSFER_FEASIBILITY_OF_THE_BRAIN_OWNED_RESIDUAL_RANKER_WITH_AN_EXTERNAL_PC_GRAPH_SUPPLIER__NO_EDGE_DISCOVERY_INTERVENABILITY_GENERAL_RCA_OR_FAMILY_CREDIT",
    "rows": rows,
    "capability_credit_delta": 0,
}

Path("rcaeval_real_transfer_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
