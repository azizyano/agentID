"""One-time preregistration. Refuses to replace an existing manifest."""

import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages/evaluation"))
from veriabstain_eval.dataset import build_manifest

target = root / "fixtures/g1a.json"
target.parent.mkdir(exist_ok=True)
raw = (json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n").encode()
with target.open("xb") as output:
    output.write(raw)
target.with_suffix(".sha256").write_text(hashlib.sha256(raw).hexdigest() + "\n", encoding="utf-8")
print("Frozen 40 synthetic scenarios; no workers executed.")
