set -e
cd /app
echo '=== FILES ==='
find . -maxdepth 3 -type f | sort
echo '=== RENDER.PY ==='
sed -n '1,260p' render.py
echo '=== IMAGE METADATA ==='
python3 - <<'PY'
from PIL import Image
from pathlib import Path
import hashlib, json
for p in [Path('/app/data/layout.png'), *sorted(Path('/app/data/components').glob('component_*.png'))]:
    im=Image.open(p).convert('RGBA')
    a=im.getchannel('A')
    print(json.dumps({
      'path':str(p.relative_to('/app')),
      'size':im.size,
      'bbox':a.getbbox(),
      'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
      'corner_pixels':[im.getpixel((0,0)),im.getpixel((im.width-1,0)),im.getpixel((0,im.height-1)),im.getpixel((im.width-1,im.height-1))]
    }))
PY
echo '=== FONTS ==='
find /app -maxdepth 4 -type f \( -name '*.ttf' -o -name '*.otf' -o -name '*.woff*' \) | sort
