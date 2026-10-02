from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
CAP=ROOT/"canonical"
EXPECTED={
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"af83f4899169e81017767c3316ddcf6b61da5ef6",
"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json":"15589dccf0bc9109594a791d702bfc93d5795c4d",
"canonical/runtime/acceptance_ir_compiler_v1.py":"c6961bcd87e16c9ff63b4c365e8547a0885b2eb4",
"canonical/runtime/terminal_next_action_compiler_v1.py":"2f07e4132ab112ef6aa40f0c2ad05f1049edb287",
"canonical/tests/test_terminal_next_action_compiler_v1.py":"db5c6d2cdf5c1208392be48dc8a91ec32521f4da",
"canonical/verification/OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"dc3045403cabfc2adac373afb7089647bb971635",
}
def sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
class ExactBrainBlobTests(unittest.TestCase):
    def test_exact_blobs(self):
        for rel,want in EXPECTED.items():
            p=CAP/rel.removeprefix("canonical/")
            self.assertEqual(sha(p),want,rel)
if __name__=="__main__":
    unittest.main(verbosity=2)
