from __future__ import annotations
import ast, hashlib, pathlib
P=pathlib.Path("subject/livebench_v7_d977_launcher_20261004/launch_livebench_v7_sanitized_atomic.py")
EXPECTED="d977690efd97e093b28474d23b37ee6e4520ed0f"
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(P)==EXPECTED,(blob(P),EXPECTED)
s=P.read_text(encoding="utf-8")
ast.parse(s)
main=s[s.index("def main()"):]
assert "atomic_claim()" in main
assert "import diagnose_livebench_replay72_v7_sanitized as diagnostic" in main
assert main.index("atomic_claim()") < main.index("import diagnose_livebench_replay72_v7_sanitized as diagnostic")
for lit in [
 'CLAIM_REF="refs/heads/livebench-v7-claims/"+EPOCH_DIGEST',
 'if status!=201:',
 'ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS',
 'ATOMIC_ONE_USE_CLAIM_RESPONSE_REF_MISMATCH',
 'terminal_dataset_read_before_claim":False',
 'execution_started_before_claim":False',
 'diagnostic.main(authorized=True,activation_blob=activation_blob)',
]:
 assert lit in s,lit
assert "download_dataset" not in s
assert "parse_population" not in s
assert "case_73" not in s.lower()
print("PASS__EXACT_D977_LAUNCHER__ATOMIC_CREATE_PRECEDES_DIAGNOSTIC__ZERO_CASES")
