import json
import subprocess
from pathlib import Path

SOURCE=Path("session_bridge/controller.py").read_text()

def test_controller_uses_live_control_fetch_for_terminal_authorization():
    assert 'auth_text = fetch_control_text("session_bridge/terminal_authorization.json")' in SOURCE
    assert 'auth_path = ROOT / "session_bridge" / "terminal_authorization.json"' not in SOURCE

def test_fetch_command_and_authorization_share_live_fetch_primitive():
    assert "def fetch_control_text(rel: str):" in SOURCE
    assert 'return fetch_control_text(f"session_bridge/commands/{step:03d}.sh")' in SOURCE

def test_python_compiles():
    subprocess.run(["python","-m","py_compile","session_bridge/controller.py"],check=True)
