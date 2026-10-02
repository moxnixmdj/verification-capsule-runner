import hashlib
from pathlib import Path
from canonical.runtime.p1_trajectory_t0_t2_multiplex_preflight import evaluate

ROOT=Path(__file__).resolve().parents[2]
def pytest_sessionstart(session):
    p=ROOT/"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
    b=p.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert sha=="8703c6aa08227467a619a7ae90d0d61f8e54da39"
    out=evaluate(ROOT)
    assert out["pass"], out
