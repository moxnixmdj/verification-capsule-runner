from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
from pyoperon.sklearn import SymbolicRegressor

OUT=Path("/tmp/h100_pyoperon_public_falsifier_v1.json")

def nrmse(y,p):
    y=np.asarray(y,dtype=float); p=np.asarray(p,dtype=float)
    rmse=float(np.sqrt(np.mean((y-p)**2)))
    scale=max(float(np.std(y)),float(np.max(np.abs(y)))*1e-9,1e-12)
    return rmse/scale

def fit_case(name,X,y,oracle,bounds,log_axes):
    X=np.asfortranarray(np.asarray(X,dtype=float))
    y=np.asarray(y,dtype=float)
    y_scale=max(float(np.std(y)),1e-12)
    ys=y/y_scale
    reg=SymbolicRegressor(
        allowed_symbols="add,sub,mul,div,powabs,sqrtabs,logabs,constant,variable",
        objectives=["nmse","length"],
        optimizer="lm",
        optimizer_iterations=15,
        population_size=800,
        pool_size=800,
        generations=800,
        max_evaluations=450_000,
        max_length=45,
        max_depth=12,
        initialization_max_length=12,
        initialization_max_depth=6,
        tournament_size=7,
        model_selection_criterion="mean_squared_error",
        n_threads=2,
        max_time=300,
        random_state=0,
    )
    t0=time.perf_counter()
    reg.fit(X,ys)
    wall=time.perf_counter()-t0

    axes=[]
    for (lo,hi),islog in zip(bounds,log_axes):
        axes.append(np.geomspace(lo,hi,17) if islog else np.linspace(lo,hi,17))
    grid=np.asfortranarray(np.array([(a,b) for a in axes[0] for b in axes[1]],dtype=float))
    truth=np.array([oracle(a,b) for a,b in grid],dtype=float)/y_scale
    pred=np.asarray(reg.predict(grid),dtype=float)
    train_pred=np.asarray(reg.predict(X),dtype=float)
    front=[]
    for row in reg.pareto_front_:
        front.append({
            "model":row.get("model"),
            "length":row.get("length"),
            "complexity":row.get("complexity"),
            "mean_squared_error":row.get("mean_squared_error"),
        })
    return {
        "name":name,
        "model":next((row["model"] for row in front if row["mean_squared_error"]==min(r["mean_squared_error"] for r in front)),None) if front else None,
        "train_nrmse":nrmse(ys,train_pred),
        "dense_oracle_nrmse":nrmse(truth,pred),
        "wall_s":wall,
        "stats":reg.stats_,
        "pareto_front":front,
    }

mu=1.7707; a=.9128; b=1.9124; c=1.6447
def blood_oracle(x1,x2):
    return mu*(1+a*x1/(1-x1)**b)*(1+c/(1+math.sqrt(x2)))
blood_X=[(.5944,1.9188),(.5044,.2068),(.05,.05),(.70,.05),(.05,30.0),(.70,30.0),(.375,1.225)]
blood_y=[12.2245,10.3732,4.3715,30.6686,2.3912,16.3743,5.7241]

def cb_oracle(x1,x2):
    return 0.3+0.62*x1**0.5*x2**(1/3)/(1+(0.4/x2)**(2/3))**0.25*(1+(x1/282000)**(5/8))**(4/5)
cb_X=[(63.5657,1.2799),(4615.6906,5.3388),(1,.2),(300000,.2),(1,10.0),(300000,10.0),(547.7226,1.4142)]
cb_y=[3.3766,76.4846,.1004,277.5832,-1.1800,1263.4885,13.5045]

result={
    "schema":"PROJECT_BRAIN_H100_PYOPERON_PUBLIC_FALSIFIER_V1",
    "pyoperon_version":"0.6.1",
    "learned_parameter_bytes":0,
    "external_learned_capability_calls":0,
    "public_examples_only":True,
    "hidden_benchmark_claim":False,
    "cases":[],
}
for args in [
    ("blood_viscosity",blood_X,blood_y,blood_oracle,[(.05,.70),(.05,30.0)],[False,True]),
    ("churchill_bernstein",cb_X,cb_y,cb_oracle,[(1,300000),(.2,10.0)],[True,True]),
]:
    try:
        result["cases"].append(fit_case(*args))
    except Exception as exc:
        result["cases"].append({"name":args[0],"error":type(exc).__name__+":"+str(exc)})
OUT.write_text(json.dumps(result,indent=2,default=str))
print(json.dumps(result,indent=2,default=str))
