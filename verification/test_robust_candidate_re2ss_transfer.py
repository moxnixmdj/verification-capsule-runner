import json, pathlib
import numpy as np
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download
from verification.brain_robust_candidate_ranker import RobustCandidateRanker

REPO="phamquiluan/RCAEval"
DATASET="RE2-SS"
K=10
idx=pd.read_parquet("hf://datasets/phamquiluan/RCAEval/cases.parquet")
cols={c.lower():c for c in idx.columns}
def col(*names):
    for n in names:
        if n.lower() in cols: return cols[n.lower()]
    raise KeyError((names,list(idx.columns)))
dc=col("dataset"); cc=col("case"); fc=col("fault")
rc=col("root_cause_service","root_service"); ic=col("inject_time","injection_time")
subset=idx[idx[dc].astype(str).str.upper()==DATASET].copy()
selected=(subset.sort_values([fc,cc]).groupby(fc,sort=True,as_index=False).head(1)
          .sort_values([fc,cc]).reset_index(drop=True))
print("PRECOMMITTED_CASES",selected[[cc,fc,rc,ic]].to_dict("records"))
files=HfApi().list_repo_files(REPO,repo_type="dataset")
results=[]
for _,row in selected.iterrows():
    case=str(row[cc]); fault=str(row[fc]); root=str(row[rc]); inject=float(row[ic])
    matches=[f for f in files if f.endswith("/metrics.parquet") and case in f.split("/")]
    if not matches: matches=[f for f in files if f.endswith("metrics.parquet") and case in f]
    if len(matches)!=1: raise RuntimeError(f"metrics file resolution {case}: {matches[:10]}")
    local=hf_hub_download(REPO,matches[0],repo_type="dataset")
    df=pd.read_parquet(local).sort_values("time").reset_index(drop=True)
    names=[c for c in df.columns if c!="time"]
    x=df[names].apply(pd.to_numeric,errors="coerce").interpolate(limit_direction="both").ffill().bfill()
    normal=x.loc[df["time"].astype(float)<inject].reset_index(drop=True)
    abnormal=x.loc[df["time"].astype(float)>=inject].reset_index(drop=True)
    good=[c for c in names if len(normal[c]) and len(abnormal[c]) and np.isfinite(normal[c]).all() and np.isfinite(abnormal[c]).all()]
    ranker=RobustCandidateRanker(good).fit({c:normal[c].to_numpy(float) for c in good})
    ranked=[n for n,_ in ranker.rank({c:abnormal[c].to_numpy(float) for c in good})]
    candidates=ranked[:K]
    service_hit=any(n.split("_")[0]==root or n.startswith(root+"_") for n in candidates)
    best=next((i+1 for i,n in enumerate(ranked) if n.split("_")[0]==root or n.startswith(root+"_")),None)
    rec={"case":case,"fault":fault,"root_service":root,"n_metrics":len(good),"best_root_service_rank":best,"top10_hit":service_hit,"top10":candidates}
    print("CASE_RESULT",json.dumps(rec,sort_keys=True)); results.append(rec)
recall=sum(r["top10_hit"] for r in results)/len(results)
summary={"dataset":DATASET,"k":K,"cases":len(results),"top10_root_service_recall":recall,
         "precommitted_gate":{"min_recall":0.75,"pass":recall>=0.75},"results":results}
print("SUMMARY",json.dumps(summary,sort_keys=True))
pathlib.Path("verification/re2ss_candidate_transfer_result.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
if not summary["precommitted_gate"]["pass"]: raise SystemExit("PRECOMMITTED_RETRIEVAL_GATE_FAILED")
