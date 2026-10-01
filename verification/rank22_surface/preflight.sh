set -euo pipefail
CTX=/tmp/rank22-freecad-surface
rm -rf "$CTX"
mkdir -p "$CTX"
curl -LfsS "https://raw.githubusercontent.com/harbor-framework/terminal-bench/452bf305c6daa62fc59061d22133a7cbc7c1572e/tasks/freecad-spring-clip/environment/Dockerfile" -o "$CTX/Dockerfile"
test "$(sha1sum "$CTX/Dockerfile" | awk '{print $1}')" = "1bb433cd0994aa4f88e4e9d52040fd880e59b919"
docker build -t rank22-freecad-preflight "$CTX"
docker run --rm -v "$PWD:/evidence" rank22-freecad-preflight bash -lc '
set -euo pipefail
freecadcmd --version
python - <<"PY"
import FreeCAD as App
import Part
doc=App.newDocument("SurfacePreflight")
box=doc.addObject("PartDesign::Feature","Probe")
box.addProperty("App::PropertyLength","ProbeLength")
box.ProbeLength=1.0
box.Shape=Part.makeBox(1,1,1)
doc.recompute()
path="/app/_surface_preflight.FCStd"
doc.saveAs(path)
assert box.Shape.Solids and len(box.Shape.Solids)==1
assert box.ProbeLength.Value==1.0
App.closeDocument("SurfacePreflight")
doc2=App.openDocument(path)
assert doc2.getObject("Probe") is not None
assert len(doc2.getObject("Probe").Shape.Solids)==1
App.closeDocument(doc2.Name)
import os
os.remove(path)
print("FREECAD_EXACT_SURFACE_PREFLIGHT_PASS")
PY
test -w /app
test ! -e /app/answer.py
test ! -e /app/answer_base.FCStd
test ! -e /app/answer_edit.FCStd
'
docker image inspect rank22-freecad-preflight --format '{{json .Config}}' > rank22_freecad_surface_profile.json
