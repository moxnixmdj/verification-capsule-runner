set -e
cd /app
python3 - <<'PY'
import json
mods={}
for name in ['cv2','numpy','scipy']:
    try:
        m=__import__(name); mods[name]=getattr(m,'__version__','ok')
    except Exception as e: mods[name]='ERR:'+repr(e)
print('MODULES',json.dumps(mods))
import cv2, numpy as np
from PIL import Image
from pathlib import Path
T=cv2.imread('/app/data/layout.png',cv2.IMREAD_COLOR)
for p in sorted(Path('/app/data/components').glob('component_*.png'),key=lambda x:int(x.stem.split('_')[1])):
    a=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
    rgb=a[:,:,:3]
    alpha=a[:,:,3]
    h,w=alpha.shape
    mask=(alpha>=220).astype(np.uint8)*255
    if mask.sum()==0: mask=(alpha>=64).astype(np.uint8)*255
    if h>T.shape[0] or w>T.shape[1]:
        print(p.name,'too_large',w,h); continue
    # sparse robust edge/color mask: opaque + non-near-bg
    try:
        res=cv2.matchTemplate(T,rgb,cv2.TM_SQDIFF_NORMED,mask=mask)
        minv, maxv, minloc, maxloc=cv2.minMaxLoc(res)
        print(json.dumps({'component':p.name,'native_size':[w,h],'opaque':int((mask>0).sum()),'sqdiff':float(minv),'loc':minloc}))
    except Exception as e:
        print(p.name,'MATCH_ERR',repr(e))
PY
