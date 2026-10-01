import os
import FreeCAD as App
import Part
import Sketcher

doc=App.newDocument("Rank22StageBGenericSurfaceSmoke")
body=doc.addObject("PartDesign::Body","Body")
sketch=body.newObject("Sketcher::SketchObject","Profile")
p0=App.Vector(0,1,0); p1=App.Vector(-1,1,0); p2=App.Vector(-1,-1,0); p3=App.Vector(0,-1,0)
sketch.addGeometry([
    Part.LineSegment(p0,p1),
    Part.LineSegment(p1,p2),
    Part.LineSegment(p2,p3),
    Part.Arc(p3,App.Vector(1,0,0),p0),
],False)
wire=Part.Wire([
    Part.makeLine(p0,p1),Part.makeLine(p1,p2),Part.makeLine(p2,p3),
    Part.Arc(p3,App.Vector(1,0,0),p0).toShape(),
])
face=Part.Face(wire)
solid=face.extrude(App.Vector(0,0,1))
pad=body.newObject("PartDesign::Feature","Pad")
pad.Shape=solid
body.Tip=pad
doc.recompute()
assert len([o for o in doc.Objects if o.TypeId=="PartDesign::Body"])==1
assert not any(o.TypeId=="Part::Feature" for o in doc.Objects)
assert len(pad.Shape.Solids)==1 and pad.Shape.Volume>0
path="/tmp/rank22_stage_b_generic_surface.FCStd"
doc.saveAs(path)
App.closeDocument(doc.Name)
doc2=App.openDocument(path)
assert len([o for o in doc2.Objects if o.TypeId=="PartDesign::Body"])==1
pad2=doc2.getObject("Pad")
assert pad2 is not None and len(pad2.Shape.Solids)==1
print("RANK22_GENERIC_FREECAD_SURFACE_PASS",App.Version(),pad2.Shape.Volume)
App.closeDocument(doc2.Name)
