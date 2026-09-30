set -e
cd /app
printf '%s
' '=== TREE ==='
find /app -maxdepth 3 -type f | sort
printf '%s
' '=== REVIEW-LIKE FILES ==='
find /app -type f \( -iname '*review*' -o -iname '*threshold*' -o -iname '*migration*' \) -print
