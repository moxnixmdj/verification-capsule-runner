from __future__ import annotations
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parent
astra=(ROOT/"canonical/runtime/astra_runtime.py").read_text()
admin=(ROOT/"canonical/runtime/root3_typed_durable_admin_write_v1.py").read_text()

def fn(src,name):
    tree=ast.parse(src)
    lines=src.splitlines()
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name:
            return "\n".join(lines[node.lineno-1:node.end_lineno])
    raise AssertionError("missing function "+name)

goal=fn(astra,"_run_goal_unstamped")
public=fn(astra,"run_goal")
execute=fn(astra,"execute_step")
main=fn(astra,"main")
shell=fn(astra,"run_shell")
admin_commit=fn(admin,"commit")

assert '"stdout":summary' in goal
assert '"final_summary":summary' in goal
assert "honesty_envelope" not in public
assert "honesty_envelope" not in execute
assert "return _stamp_cognition_provenance(_run_goal_unstamped(step, mission))" in public
assert 'return run_goal(step, mission or {})' in execute
assert 'state["history"].append(rec)' in main
assert "write_statej(state_path,state)" in main
assert 'env[prefix+"RESULT_JSON"]' in shell
assert 'env[prefix+"BODY"]' in shell
assert 'env[prefix+"STDOUT"]' in shell
assert "honesty_envelope" not in admin_commit
assert "honesty_envelope_v1" not in astra
assert "compile_honesty_envelope" not in astra
print("PASS: independent current-byte load-bearing honesty bypass check")
