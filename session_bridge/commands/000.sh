set -e
cd /app
echo '===== FILES ====='
find . -maxdepth 3 -type f -printf '%p %s bytes\n' | sort
echo '===== TEXT FILES ====='
for f in ./*; do
  [ -f "$f" ] || continue
  case "$f" in
    *.py|*.sh|*.sql|*.json|*.toml|*.yaml|*.yml|*.md|*.txt|*.conf|*.ini)
      echo "===== $f ====="
      sed -n '1,420p' "$f"
      ;;
  esac
done
