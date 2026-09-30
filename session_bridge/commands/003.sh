set -e
echo '=== PYTHON / CORPUS AVAILABILITY ==='
python3 - <<'PY'
mods=['wordfreq','wordninja','wordfreq','nltk','spacy','wordfreq','scipy','numpy']
for m in mods:
    try:
        mod=__import__(m); print(m,'YES',getattr(mod,'__version__',''))
    except Exception as e:
        print(m,'NO',type(e).__name__)
import pathlib
for p in ['/usr/share/dict','/usr/share/hunspell','/usr/share/myspell','/usr/local/lib/python3.11/site-packages']:
    q=pathlib.Path(p)
    print('PATH',p,'EXISTS',q.exists())
    if q.exists() and p!='/usr/local/lib/python3.11/site-packages':
        print([str(x) for x in list(q.glob('*'))[:30]])
PY
