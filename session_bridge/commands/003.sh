set -euo pipefail
printf '%s\n' '--- root ---'
ls -la /
printf '%s\n' '--- likely state dirs ---'
for d in /data /state /var/lib /run /tmp; do
  if [ -e "$d" ]; then echo "### $d"; ls -la "$d" | head -80; fi
done
printf '%s\n' '--- mounts ---'
mount | sed -n '1,160p'
printf '%s\n' '--- relevant env/all hints ---'
env | sort | sed -n '1,200p'
