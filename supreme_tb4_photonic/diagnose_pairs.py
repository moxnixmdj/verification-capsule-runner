#!/usr/bin/env python3
import importlib.util,json,pathlib,sys,math
root=pathlib.Path.cwd()
p=root/'terminal-bench/tasks/photonic-waveguide-routing/environment/check_routing.py'
spec=importlib.util.spec_from_file_location('checker',p); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
data=json.loads((root/'supreme_tb4_photonic/routing_result_1.json').read_text())
phys={nid:m.build_physical_path(nd['waypoints'],n_arc=64) for nid,nd in data['nets'].items()}
pairs=[('net_00','net_08'),('net_02','net_04'),('net_03','net_04'),('net_03','net_05')]
out={}
for a,b in pairs:
    best=(1e99,None)
    crossings=[]
    for i in range(len(phys[a])-1):
      a1,a2=phys[a][i],phys[a][i+1]
      if m.seg_length(a1,a2)<1e-9: continue
      for j in range(len(phys[b])-1):
        b1,b2=phys[b][j],phys[b][j+1]
        if m.seg_length(b1,b2)<1e-9: continue
        if m.segments_intersect(a1,a2,b1,b2):
          crossings.append({'a_seg':i,'b_seg':j,'a':[a1,a2],'b':[b1,b2]})
          d=0.0
        else:d=m.min_dist_seg_seg(a1,a2,b1,b2)
        if d<best[0]: best=(d,{'a_seg':i,'b_seg':j,'a':[a1,a2],'b':[b1,b2]})
    out[a+'<->'+b]={'minimum_distance':best[0],'minimum_geometry':best[1],'crossing_count':len(crossings),'crossings':crossings[:12]}
print(json.dumps(out,indent=2,sort_keys=True))
(root/'supreme_tb4_photonic/evidence/pair-diagnostic.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
