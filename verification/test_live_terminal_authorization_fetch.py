import subprocess
from pathlib import Path

SOURCE=Path("session_bridge/controller.py").read_text()

assert 'auth_text = fetch_control_text("session_bridge/terminal_authorization.json")' in SOURCE
assert 'auth_path = ROOT / "session_bridge" / "terminal_authorization.json"' not in SOURCE
assert "def fetch_control_text(rel: str):" in SOURCE
assert 'return fetch_control_text(f"session_bridge/commands/{step:03d}.sh")' in SOURCE
subprocess.run(["python","-m","py_compile","session_bridge/controller.py"],check=True)
print("LIVE_TERMINAL_AUTHORIZATION_FETCH_REGRESSION_PASS")
