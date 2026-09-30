#!/usr/bin/env python3
import importlib.util, json, math, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
checker_path=ROOT/"terminal-bench/tasks/photonic-waveguide-routing/environment/check_routing.py"
spec=importlib.util.spec_from_file_location("checker",checker_path)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
data=json.loads((ROOT/"supreme_tb4_photonic/routing_result_1.json").read_text())
physical={nid:m.build_physical_path(nd["waypoints"],n_arc=64) for nid,nd in data["nets"].items()}
pairs=[]
ids=sorted(physical)
for i,a in enumerate(ids):
  for b in ids[i+1:]:
    best=(1e99,None)
    crossings=[]
    sa=[(physical[a][k],physical[a][k+1]) for k in range(len(physical[a])-1) if m.seg_length(physical[a][k],physical[a][k+1])>1e-9]
    sb=[(physical[b][k],physical[b][k+1]) for k in range(len(physical[b])-1) if m.seg_length(physical[b][k],physical[b][k+1])>1e-9]
    for ia,(a1,a2) in enumerate(sa):
      for ib,(b1,b2) in enumerate(sb):
        if m.segments_intersect(a1,a2,b1,b2):
          crossings.append({"a_seg":ia,"b_seg":ib,"a":[a1,a2],"b":[b1,b2]})
          d=0.0
        else:
          d=m.min_dist_seg_seg(a1,a2,b1,b2)
        if d<best[0]:
          best=(d,{"a_seg":ia,"b_seg":ib,"a":[a1,a2],"b":[b1,b2]})
    if best[0] < m.MIN_SEPARATION:
      pairs.append({"pair":f"{a}<->{b}","min_dist":best[0],"closest":best[1],"crossing_count":len(crossings),"first_crossings":crossings[:3]})
selfx=[]
for nid,pts in physical.items():
  segs=[(pts[k],pts[k+1]) for k in range(len(pts)-1) if m.seg_length(pts[k],pts[k+1])>1e-9]
  for i in range(len(segs)):
    for j in range(i+2,len(segs)):
      if m.segments_touch_or_overlap(segs[i][0],segs[i][1],segs[j][0],segs[j][1]):
        selfx.append({"net":nid,"a_seg":i,"b_seg":j,"a":segs[i],"b":segs[j]})
report={"pairs":pairs,"self_intersections":selfx[:20]}
out=ROOT/"supreme_tb4_photonic/evidence/diagnostic.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
