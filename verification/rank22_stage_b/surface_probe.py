import json, os, tempfile
import FreeCAD as App
import Part, Sketcher
doc=App.newDocument("StageBProbe")
body=doc.addObject("PartDesign::Body","Body")
doc.recompute()
path="/tmp/rank22_stageb_probe.FCStd"
doc.saveAs(path)
assert os.path.isfile(path)
assert len(doc.findObjects("PartDesign::Body"))==1
print(json.dumps({"freecad_version":App.Version(),"body_count":1,"saved":True}))
