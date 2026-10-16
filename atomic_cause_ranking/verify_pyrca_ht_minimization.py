import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from pyrca.analyzers.ht import HT, HTConfig

from brain_owned_ht_ranker import ResidualCauseRanker

SEED = 202610010901
TRIALS = 400
NORMAL_N = 500
ABNORMAL_N = 80
SHIFT = 6.0

rng = np.random.default_rng(SEED)
py_rng = random.Random(SEED)


def make_dag(n):
    names=[f"N{i}" for i in range(n)]
    adj=pd.DataFrame(np.zeros((n,n),dtype=int),index=names,columns=names)
    for i in range(n-1):
        adj.iloc[i,i+1]=1
    for i in range(n):
        for j in range(i+2,n):
            if py_rng.random()<0.22:
                adj.iloc[i,j]=1
    return names,adj


def parents_map(adj):
    return {n:[p for p in adj.index if int(adj.loc[p,n])!=0] for n in adj.columns}


def ancestors(adj,target):
    out=set(); stack=[target]
    while stack:
        cur=stack.pop()
        for p in adj.index:
            if int(adj.loc[p,cur])!=0 and p not in out:
                out.add(p); stack.append(p)
    return out


def simulate(adj,n_rows,intervention_node=None):
    cols=list(adj.columns)
    data=pd.DataFrame(index=range(n_rows),columns=cols,dtype=float)
    weights={}
    for i,src in enumerate(cols):
        for j,dst in enumerate(cols):
            if int(adj.loc[src,dst])!=0:
                weights[(src,dst)]=0.55+0.1*((i+j)%4)
    for node in cols:
        ps=[p for p in cols if int(adj.loc[p,node])!=0]
        value=rng.normal(0.0,1.0,size=n_rows)
        for p in ps:
            value += weights[(p,node)]*data[p].to_numpy(dtype=float)
        if node==intervention_node:
            value += SHIFT
        data[node]=value
    return data


def as_mapping(df):
    return {c:df[c].to_numpy(dtype=float) for c in df.columns}


rows=[]
top1_match=0
full_order_match=0
max_score_abs_error=0.0

for trial in range(TRIALS):
    n=py_rng.randint(5,9)
    names,adj=make_dag(n)
    target=names[-1]
    candidates=sorted(ancestors(adj,target),key=lambda x:int(x[1:]))
    true_cause=py_rng.choice(candidates)
    normal=simulate(adj,NORMAL_N)
    abnormal=simulate(adj,ABNORMAL_N,true_cause)

    donor=HT(HTConfig(graph=adj,aggregator="max",root_cause_top_k=len(names)))
    donor.train(normal)
    donor_result=donor.find_root_causes(abnormal,anomalous_metrics=target,adjustment=False)
    donor_scores={node:float(score) for node,score in donor_result.root_cause_nodes}
    donor_rank=sorted(candidates,key=lambda n:donor_scores[n],reverse=True)

    owned=ResidualCauseRanker(names,parents_map(adj)).fit(as_mapping(normal))
    owned_pairs=owned.rank(as_mapping(abnormal),candidates)
    owned_scores=dict(owned_pairs)
    owned_rank=[n for n,_ in owned_pairs]

    top1_match += int(donor_rank[0]==owned_rank[0])
    full_order_match += int(donor_rank==owned_rank)
    score_error=max(abs(donor_scores[n]-owned_scores[n]) for n in candidates)
    max_score_abs_error=max(max_score_abs_error,score_error)

    rows.append({
        "trial":trial,
        "true_cause":true_cause,
        "donor_top1":donor_rank[0],
        "owned_top1":owned_rank[0],
        "top1_match":donor_rank[0]==owned_rank[0],
        "full_order_match":donor_rank==owned_rank,
        "max_candidate_score_abs_error":score_error,
    })

result={
    "schema":"PROJECT_BRAIN_PYRCA_HT_DONOR_MINIMIZATION_DIFFERENTIAL_V1",
    "status":"DONOR_MINIMIZATION_DIFFERENTIAL__ZERO_CAPABILITY_CREDIT",
    "seed":SEED,
    "fresh_trials":TRIALS,
    "donor":{
        "repo":"salesforce/PyRCA",
        "revision":"411310d589fac5cb8e7bdce67d33eadb091a1083",
        "algorithm":"HT",
        "license":"BSD-3-Clause"
    },
    "brain_owned_candidate":{
        "path":"atomic_cause_ranking/brain_owned_ht_ranker.py",
        "external_runtime_dependencies":["numpy"],
        "pyrca_runtime_required":False,
        "sklearn_runtime_required":False,
        "scipy_runtime_required":False,
        "pandas_runtime_required":False,
        "networkx_runtime_required":False
    },
    "metrics":{
        "top1_equivalence_fraction":top1_match/TRIALS,
        "full_candidate_order_equivalence_fraction":full_order_match/TRIALS,
        "max_candidate_score_abs_error":max_score_abs_error
    },
    "gate":{
        "min_top1_equivalence_fraction":1.0,
        "min_full_order_equivalence_fraction":0.995,
        "max_candidate_score_abs_error":1e-8,
        "pass":(top1_match==TRIALS and full_order_match/TRIALS>=0.995 and max_score_abs_error<=1e-8)
    },
    "interpretation_rule":"PASS_SUPPORTS_ONLY_DONOR_INDEPENDENT_EQUIVALENCE_OF_THE_PYRCA_HT_RESIDUAL_SCORING_AND_RANKING_SLICE_ON_FRESH_EXPLICIT_NUMERIC_DAGS__REAL_TRACE_TRANSFER_AND_GENERAL_RCA_REMAIN_UNPROVEN",
    "rows":rows,
    "capability_credit_delta":0
}
p=Path("pyrca_ht_minimization_result.json")
p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
if not result["gate"]["pass"]:
    raise SystemExit(1)
