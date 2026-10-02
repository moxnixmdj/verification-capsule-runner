from pathlib import Path
import hashlib

ROOT=Path("capsules/cad_render_antishortcut_repair_v1")
EXPECTED={
 "canonical/runtime/cad_t0_route_specific_candidate_v1.py":"badbce2b330cd4a8e1c64e2f0fa88f79123a94f2",
 "canonical/tests/test_cad_t0_source_structure_antishortcut_repair_v1.py":"50a3eeed9b4b0c141f7019e3c569d233d4840b95",
}
def git_blob(path):
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def test_exact_brain_blob_binding():
 for rel,expected in EXPECTED.items():
  got=git_blob(ROOT/rel)
  assert got==expected,(rel,got,expected)
