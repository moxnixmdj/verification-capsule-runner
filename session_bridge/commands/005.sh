set -euo pipefail
cat >> /app/tests/test_worker_unit.py <<'PY'

if __name__ == "__main__":
    test_checkpoint_roundtrip()
    test_apply_transaction_is_duplicate_safe()
    test_post_overdraft_uses_transaction_id_as_idempotency_key()
    print("UNIT_TESTS_PASS")
PY
cd /app/src
PYTHONPATH=/app/src python3 /app/tests/test_worker_unit.py
