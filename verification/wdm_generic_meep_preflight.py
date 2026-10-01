import json, time
import numpy as np
import meep as mp

result={"schema":"WDM_STAGE_B_GENERIC_MEEP_PREFLIGHT_V1","task_execution":False}

result["meep_import"]=True
result["meep_version"]=getattr(mp,"__version__","unknown")
result["odd_z_available"]=hasattr(mp,"ODD_Z")
result["no_direction_available"]=hasattr(mp,"NO_DIRECTION")

clad=mp.Medium(index=1.44)
core=mp.Medium(index=2.85)
weights=np.zeros((8,8),dtype=float)
weights[2:6,3:5]=1.0
grid=mp.MaterialGrid(mp.Vector3(8,8),clad,core,weights=weights,grid_type="U_MEAN")
result["material_grid_created"]=grid is not None

cell=mp.Vector3(3.0,2.4,0)
geometry=[
    mp.Block(center=mp.Vector3(),size=mp.Vector3(mp.inf,0.45,mp.inf),material=core)
]
sources=[
    mp.EigenModeSource(
        src=mp.GaussianSource(frequency=1/1.55,fwidth=0.05),
        center=mp.Vector3(-0.8,0),
        size=mp.Vector3(0,1.6,0),
        eig_band=1,
        direction=mp.NO_DIRECTION,
        eig_kpoint=mp.Vector3(1,0,0),
        eig_parity=mp.ODD_Z,
    )
]
sim=mp.Simulation(
    cell_size=cell,
    boundary_layers=[mp.PML(0.3)],
    geometry=geometry,
    sources=sources,
    default_material=clad,
    resolution=15,
    dimensions=2,
)
t0=time.monotonic()
sim.run(until=2)
elapsed=time.monotonic()-t0
result["tiny_fdtd_completed"]=True
result["tiny_fdtd_elapsed_sec"]=elapsed
result["bounded_under_120_sec"]=elapsed < 120
result["pass"]=all([
    result["meep_import"],result["odd_z_available"],result["no_direction_available"],
    result["material_grid_created"],result["tiny_fdtd_completed"],result["bounded_under_120_sec"]
])
print(json.dumps(result,sort_keys=True))
if not result["pass"]:
    raise SystemExit(1)
