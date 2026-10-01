import os, tempfile
import FreeCAD as App
import PartDesign

tmp=tempfile.mkdtemp(prefix="brain-freecad-stageb-")
doc=App.newDocument("GenericSmoke")
body=doc.addObject("PartDesign::Body","Body")
body.Label="Body"
body.addProperty("App::PropertyInteger","Count","Parameters")
body.Count=12

box=doc.addObject("PartDesign::AdditiveBox","Base")
box.Length=20
box.Width=20
box.Height=5
body.addObject(box)

cyl=doc.addObject("PartDesign::AdditiveCylinder","Hub")
cyl.Radius=4
cyl.Height=8
cyl.Placement.Base=App.Vector(10,10,5)
body.addObject(cyl)

doc.recompute()
assert len(doc.getObjectsByLabel("Body"))==1
assert body.Tip is not None
assert not body.Tip.Shape.isNull()
assert body.Tip.Shape.Solids and len(body.Tip.Shape.Solids)==1

loft=doc.addObject("PartDesign::AdditiveLoft","LoftProbe")
body.addObject(loft)
assert "Sections" in loft.PropertiesList or "Profile" in loft.PropertiesList
doc.removeObject(loft.Name)

pat=doc.addObject("PartDesign::PolarPattern","PatternProbe")
body.addObject(pat)
assert "Occurrences" in pat.PropertiesList
assert "Angle" in pat.PropertiesList
doc.removeObject(pat.Name)

base=os.path.join(tmp,"generic.FCStd")
doc.recompute()
doc.saveAs(base)
App.closeDocument(doc.Name)

doc2=App.openDocument(base)
b2=doc2.getObject("Body")
assert b2 is not None
assert b2.Count==12
b2.Count=6
doc2.recompute()
edit=os.path.join(tmp,"generic_edit.FCStd")
doc2.saveAs(edit)
App.closeDocument(doc2.Name)
assert os.path.getsize(base)>0 and os.path.getsize(edit)>0
print("GENERIC_FREECAD_STAGE_B_SMOKE_PASS",base,edit)
