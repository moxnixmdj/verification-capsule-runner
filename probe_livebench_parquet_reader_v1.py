#!/usr/bin/env python3
import hashlib, importlib.util, pathlib, subprocess, sys

print("PYTHON", sys.version)
for name in ("pyarrow", "pyarrow.parquet", "pandas"):
    spec=importlib.util.find_spec(name)
    print("AVAILABLE", name, bool(spec))
if importlib.util.find_spec("pyarrow") is not None:
    import pyarrow
    print("PYARROW_VERSION", pyarrow.__version__)
else:
    out=pathlib.Path("/tmp/livebench-reader-wheel")
    out.mkdir(parents=True,exist_ok=True)
    subprocess.run([
        sys.executable,"-m","pip","download","--no-deps","--only-binary=:all:",
        "--dest",str(out),"pyarrow==20.0.0"
    ],check=True)
    files=list(out.iterdir())
    assert len(files)==1, files
    p=files[0]
    print("CANDIDATE_WHEEL",p.name)
    print("CANDIDATE_WHEEL_SHA256",hashlib.sha256(p.read_bytes()).hexdigest())
print("PASS_ZERO_CASE_READER_PROBE")
