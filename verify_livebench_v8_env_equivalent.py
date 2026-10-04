from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V8 = ROOT / "diagnose_livebench_replay72_v8_env_equivalent.py"
V7 = ROOT / "diagnose_livebench_replay72_v7_sanitized.py"
CLASSIFIER = ROOT / "livebench_v7_sanitized_classifier.py"
BASE = ROOT / "execute_livebench_if_replay72_v4_candidate.py"

EXPECTED = {
    V7: "e9a5a5937b19e76bf04444c288e3a75113874ed7",
    CLASSIFIER: "44df7313c83914204299953dda81900fae85ab68",
    BASE: "2a57ce896ddbd6819246aab8b44d17a00f36b61e",
}


def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


for path, expected in EXPECTED.items():
    got = blob_sha(path)
    assert got == expected, (path.name, got, expected)

src = V8.read_text(encoding="utf-8")
ast.parse(src)

required_literals = [
    "mod.install_scorer_deps()",
    "mod.prepare_nltk(base)",
    "mod.clone_livebench(base)",
    "SYNTHETIC_LEGACY_SCORER_SMOKE",
    "SYNTHETIC_IFBENCH_SCORER_SMOKE",
    "template = prepare_v6_equivalent_precase(base, mod)",
    "parquet = mod.download_dataset(base)",
    "REPLAY_LIMIT = 72",
    '"case_ids_emitted": False',
    '"prompt_text_emitted": False',
    '"response_text_emitted": False',
    '"raw_exception_text_emitted": False',
    '"v6_precase_environment_equivalence": True',
]
for item in required_literals:
    assert item in src, item

# Environment preparation must occur before terminal dataset download.
prep_pos = src.index("template = prepare_v6_equivalent_precase(base, mod)")
download_pos = src.index("parquet = mod.download_dataset(base)")
assert prep_pos < download_pos

# Exact V6 precase operations occur in the same required order.
positions = [
    src.index("mod.install_scorer_deps()"),
    src.index("mod.prepare_nltk(base)"),
    src.index("mod.clone_livebench(base)"),
    src.index("SYNTHETIC_LEGACY_SCORER_SMOKE"),
    src.index("SYNTHETIC_IFBENCH_SCORER_SMOKE"),
]
assert positions == sorted(positions)

# The diagnostic must not authorize new cases, acceptance, or promotion.
assert '"new_case_exposure": False' in src
assert '"acceptance_credit_authority": False' in src
assert '"promotion_authority": False' in src
assert "CASE_73" not in src
assert "questions[:REPLAY_LIMIT]" not in src  # exact fixed loop is used instead
assert "range(0, REPLAY_LIMIT" in src

# It reuses the independently verified sanitized classifier rather than emitting raw errors.
assert "v7.classify_one" in src
assert "raw_exception" not in src.lower() or '"raw_exception_text_emitted": False' in src

print("LIVEBENCH_V8_ENV_EQUIVALENCE_STATIC_VERIFICATION=PASS")
