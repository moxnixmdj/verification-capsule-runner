set -e
cd /app
python3 - <<'PY'
from PIL import Image
from pathlib import Path
from collections import Counter,defaultdict
import json

target=Image.open('/app/data/layout.png').convert('RGB')
tw,th=target.size
tpx=target.load()
freq=Counter(target.getdata())
pos=defaultdict(list)
for y in range(th):
    for x in range(tw):
        c=tpx[x,y]
        if freq[c] <= 80:
            pos[c].append((x,y))

for p in sorted(Path('/app/data/components').glob('component_*.png'),key=lambda q:int(q.stem.split('_')[1])):
    im=Image.open(p).convert('RGBA'); w,h=im.size; pix=im.load()
    candidates=[]
    # Prefer fully opaque pixels whose colors are rare in target and spread spatially.
    for y in range(h):
        for x in range(w):
            r,g,b,a=pix[x,y]
            if a==255:
                n=freq[(r,g,b)]
                if 0<n<=80:
                    candidates.append((n,x,y,(r,g,b)))
    candidates.sort(key=lambda z:(z[0],z[2],z[1]))
    # spatially diverse subset
    chosen=[]; cells=set()
    for row in candidates:
        _,x,y,c=row
        cell=(x//max(1,w//8 or 1),y//max(1,h//8 or 1))
        if cell not in cells or len(chosen)<32:
            chosen.append(row); cells.add(cell)
        if len(chosen)>=160: break
    votes=Counter()
    for _,x,y,c in chosen:
        for tx,ty in pos[c]:
            dx,dy=tx-x,ty-y
            if dx>=-w and dy>=-h and dx<tw and dy<th:
                votes[(dx,dy)] += 1
    top=votes.most_common(8)
    print(json.dumps({
      'component':p.name,'size':[w,h],
      'rare_opaque_candidates':len(candidates),'used':len(chosen),
      'top_native_translation_votes':[[list(k),v] for k,v in top]
    }))
PY
