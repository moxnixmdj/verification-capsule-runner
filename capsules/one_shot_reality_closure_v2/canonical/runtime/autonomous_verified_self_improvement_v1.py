import json
from pathlib import Path

DEFAULT_STATE_PATH = Path(__file__).with_name("_state.json")

def _empty_state():
    return {
        "observations": {},
        "failures": {},
        "episodes": {},
        "skills": {},
        "improvement_queue": {},
        "stats": {},
    }

def load_state(path=DEFAULT_STATE_PATH):
    p = Path(path)
    if not p.exists():
        return _empty_state()
    return json.loads(p.read_text(encoding="utf-8"))

def _write_state(state, path=DEFAULT_STATE_PATH):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return state
