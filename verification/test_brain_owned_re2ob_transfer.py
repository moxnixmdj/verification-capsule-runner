import json, os, pathlib, tempfile
import numpy as np
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

from verification.brain_pc_stable_cpdag import pc_stable_cpdag
from verification.brain_causal_residual_ranker import ResidualCauseRanker

REPO="phamquiluan/RCAEval"
DATASET="RE2-OB"
MAX_K=1
ALPHA=0.05

idx=pd.read_parquet("hf://datasets/phamquiluan/RCAEval/cases.parquet")
cols={c.lower():c for c in idx.columns}
def col(*names):
    for n in names:
        if n.lower() in cols:
            return cols[n.lower()]
    raise KeyError((names,list(idx.columns)))
dataset_col=col("dataset")
case_col=col("case")
fault_col=col("fault")
root_col=col("root_cause_service","root_service")
inject_col=col("inject_time","injection_time")

subset=idx[idx[dataset_col].astype(str).str.upper()==DATASET].copy()
if subset.empty:
    raise RuntimeError(f"no rows for {DATASET}; datasets={sorted(idx[dataset_col].astype(str).unique())[:20]}")
# Freeze exactly one lexicographically first case per fault before reading telemetry.
selected=(subset.sort_values([fault_col,case_col]).groupby(fault_col,sort=True,as_index=False).head(1))
selected=selected.sort_values([fault_col,case_col]).reset_index(drop=True)
print("PRECOMMITTED_CASES",selected[[case_col,fault_col,root_col,inject_col]].to_dict("records"))

api=HfApi()
repo_files=api.list_repo_files(REPO,repo_type="dataset")
results=[]
for _,row in selected.iterrows():
    case=str(row[case_col])
    fault=str(row[fault_col])
    root=str(row[root_col])
    inject=float(row[inject_col])
    matches=[f for f in repo_files if f.endswith("/metrics.parquet") and case in f.split("/")]
    if not matches:
        matches=[f for f in repo_files if f.endswith("metrics.parquet") and case in f]
    if len(matches)!=1:
        raise RuntimeError(f"metrics file resolution for {case}: {matches[:10]}")
    local=hf_hub_download(REPO,matches[0],repo_type="dataset")
    df=pd.read_parquet(local).sort_values("time").reset_index(drop=True)
    names=[c for c in df.columns if c!="time"]
    x=df[names].apply(pd.to_numeric,errors="coerce")
    x=x.interpolate(limit_direction="both").ffill().bfill()
    # Remove variables unusable by the owned continuous-complete-data mechanism,
    # based only on normal/reference data.
    normal_mask=df["time"].astype(float)<inject
    abnormal_mask=~normal_mask
    if normal_mask.sum()<20 or abnormal_mask.sum()<5:
        raise RuntimeError(f"insufficient split {case}: normal={normal_mask.sum()} abnormal={abnormal_mask.sum()}")
    normal=x.loc[normal_mask].reset_index(drop=True)
    abnormal=x.loc[abnormal_mask].reset_index(drop=True)
    good=[c for c in names if np.isfinite(normal[c]).all() and np.isfinite(abnormal[c]).all() and float(normal[c].std(ddof=0))>1e-12]
    normal=normal[good]
    abnormal=abnormal[good]
    data=normal.to_numpy(float)
    cpdag,skeleton,seps=pc_stable_cpdag(data,alpha=ALPHA,max_k=MAX_K)
    parents={}
    for v,name in enumerate(good):
        parents[name]=[good[u] for u in range(len(good)) if cpdag[u,v] and not cpdag[v,u]]
    ranker=ResidualCauseRanker(good,parents).fit({c:normal[c].to_numpy(float) for c in good})
    ranking=ranker.rank({c:abnormal[c].to_numpy(float) for c in good})
    ranked=[n for n,_ in ranking]
    service_ranks=[i+1 for i,n in enumerate(ranked) if n.split("_")[0]==root or n.startswith(root+"_")]
    best=min(service_ranks) if service_ranks else None
    directed=int(sum(1 for u in range(len(good)) for v in range(len(good)) if cpdag[u,v] and not cpdag[v,u]))
    undirected=int(sum(1 for u in range(len(good)) for v in range(u+1,len(good)) if cpdag[u,v] and cpdag[v,u]))
    rec={"case":case,"fault":fault,"root_service":root,"n_metrics":len(good),"best_root_service_rank":best,
         "top5":best is not None and best<=5,"top10":best is not None and best<=10,
         "directed_arcs":directed,"undirected_edges":undirected,
         "top10_metrics":ranked[:10]}
    print("CASE_RESULT",json.dumps(rec,sort_keys=True))
    results.append(rec)

top5=sum(r["top5"] for r in results)/len(results)
top10=sum(r["top10"] for r in results)/len(results)
summary={"dataset":DATASET,"cases":len(results),"faults":[r["fault"] for r in results],
         "root_service_top5_fraction":top5,"root_service_top10_fraction":top10,
         "alpha":ALPHA,"max_k":MAX_K,
         "gate":{"min_top5":0.5,"min_top10":0.75,
                 "pass":top5>=0.5 and top10>=0.75},
         "results":results}
print("SUMMARY",json.dumps(summary,sort_keys=True))
pathlib.Path("verification/re2ob_transfer_result.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
if not summary["gate"]["pass"]:
    raise SystemExit("PRECOMMITTED_TRANSFER_GATE_FAILED")
