set -e
cd /app
printf '===== APP =====\n'
find . -maxdepth 3 -type f -not -path './.git/*' -print | sort
for f in $(find . -maxdepth 2 -type f -not -path './.git/*' | sort); do
  echo "\n--- $f ---"
  sed -n '1,260p' "$f"
done
printf '\n===== PYTHON =====\n'
python3 --version
python3 - <<'PY'
mods=['bs4','html5lib','lxml','bleach']
for m in mods:
    try:
        mod=__import__(m)
        print(m,'AVAILABLE',getattr(mod,'__version__',''))
    except Exception as e:
        print(m,'UNAVAILABLE',type(e).__name__,str(e))
PY
