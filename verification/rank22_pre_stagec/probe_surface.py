import json, os, platform
import FreeCAD as App
out={}
out["python"]=platform.python_version()
out["freecad_version"]=".".join(map(str,App.Version()[:3]))
out["cwd"]=os.getcwd()
out["app_writable"]=os.access("/app",os.W_OK)
doc=App.newDocument("SurfaceProbe")
obj=doc.addObject("App::FeaturePython","SurfaceProbe")
obj.addProperty("App::PropertyString","Purpose")
obj.Purpose="GENERIC_EXECUTION_SURFACE_PREFLIGHT_ONLY"
doc.recompute()
path="/app/_surface_probe.FCStd"
doc.saveAs(path)
App.closeDocument(doc.Name)
doc2=App.openDocument(path)
out["fcstd_roundtrip"]=doc2 is not None and doc2.getObject("SurfaceProbe") is not None
App.closeDocument(doc2.Name)
out["file_exists"]=os.path.exists(path) and os.path.getsize(path)>0
out["pass"]=(
  out["freecad_version"].startswith("0.21.2")
  and out["python"].startswith("3.11")
  and out["cwd"]=="/app"
  and out["app_writable"]
  and out["fcstd_roundtrip"]
  and out["file_exists"]
)
with open("/app/surface_receipt.json","w") as f: json.dump(out,f,sort_keys=True,indent=2)
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
