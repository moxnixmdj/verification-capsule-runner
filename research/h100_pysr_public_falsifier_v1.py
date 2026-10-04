from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import sympy as sp
from pysr import PySRRegressor

OUT = Path("/tmp/h100_pysr_public_falsifier_v1.json")

def nrmse(y, pred):
    y=np.asarray(y,dtype=float); pred=np.asarray(pred,dtype=float)
    rmse=float(np.sqrt(np.mean((y-pred)**2)))
    scale=max(float(np.std(y)), float(np.max(np.abs(y)))*1e-9, 1e-12)
    return rmse/scale

def fit_case(name, X, y, oracle, bounds, log_axes):
    X=np.asarray(X,dtype=float)
    y=np.asarray(y,dtype=float)
    y_scale=max(float(np.std(y)),1e-12)
    ys=y/y_scale

    model=PySRRegressor(
        niterations=180,
        populations=12,
        population_size=48,
        maxsize=36,
        maxdepth=14,
        binary_operators=["+","-","*","/","^"],
        unary_operators=["sqrt_abs(x) = sqrt(abs(x))"],
        extra_sympy_mappings={"sqrt_abs": lambda x: sp.sqrt(sp.Abs(x))},
        random_state=0,
        deterministic=True,
        parallelism="serial",
        progress=False,
        verbosity=0,
        model_selection="accuracy",
        constraints={"^": (-1, 1)},
        nested_constraints={"^": {"^": 0}},
    )
    t0=time.perf_counter()
    model.fit(X,ys)
    wall=time.perf_counter()-t0
    expr=model.sympy()
    x0,x1=sp.symbols("x0 x1")
    fn=sp.lambdify((x0,x1),expr,"numpy")

    axes=[]
    for (lo,hi),islog in zip(bounds,log_axes):
        axes.append(np.geomspace(lo,hi,17) if islog else np.linspace(lo,hi,17))
    grid=np.array([(a,b) for a in axes[0] for b in axes[1]],dtype=float)
    truth=np.array([oracle(a,b) for a,b in grid],dtype=float)/y_scale
    raw=fn(grid[:,0],grid[:,1])
    pred=np.asarray(raw,dtype=float)
    if pred.ndim==0:
        pred=np.full_like(truth,float(pred))
    pred=np.reshape(pred,truth.shape)
    dense_err=nrmse(truth,pred)
    train_pred=np.asarray(fn(X[:,0],X[:,1]),dtype=float)
    if train_pred.ndim==0:
        train_pred=np.full_like(ys,float(train_pred))
    train_pred=np.reshape(train_pred,ys.shape)
    return {
        "name":name,
        "equation_scaled_target":str(expr),
        "y_scale":y_scale,
        "train_nrmse":nrmse(ys,train_pred),
        "dense_oracle_nrmse":dense_err,
        "wall_s":wall,
        "equation_table":model.equations_[["complexity","loss","score","equation"]].tail(12).to_dict(orient="records"),
    }

mu=1.7707; a=.9128; b=1.9124; c=1.6447
def blood_oracle(x1,x2):
    return mu*(1+a*x1/(1-x1)**b)*(1+c/(1+math.sqrt(x2)))

blood_X=[
    (.5944,1.9188),(.5044,.2068),(.05,.05),(.70,.05),(.05,30.0),(.70,30.0),(.375,1.225)
]
blood_y=[12.2245,10.3732,4.3715,30.6686,2.3912,16.3743,5.7241]

def cb_oracle(x1,x2):
    return 1.0*(0.3+0.62*x1**0.5*x2**(1/3)/(1+(0.4/x2)**(2/3))**0.25*(1+(x1/282000)**(5/8))**(4/5))

cb_X=[
    (63.5657,1.2799),(4615.6906,5.3388),(1,.2),(300000,.2),(1,10.0),(300000,10.0),(547.7226,1.4142)
]
cb_y=[3.3766,76.4846,.1004,277.5832,-1.1800,1263.4885,13.5045]

result={
    "schema":"PROJECT_BRAIN_H100_PYSR_PUBLIC_FALSIFIER_V1",
    "pysr_version":"2.6.0",
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

OUT.write_text(json.dumps(result,indent=2,default=float))
print(json.dumps(result,indent=2,default=float))
