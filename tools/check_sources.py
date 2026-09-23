"""Check the pristine Arduino snapshot against its recorded SHA256 manifest."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
vendor = root / "third_party/arduino-stk500v2"
manifest = json.loads((vendor / "SHA256SUMS.json").read_text())
for name, expected in manifest.items():
    actual = hashlib.sha256((vendor / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"FAIL: vendored source has changed: {name}")
print(f"PASS: {len(manifest)} pinned Arduino source files verified")
notices = json.loads((root / "third_party/licenses/SOURCES.json").read_text())
for entry in notices:
    actual = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        raise SystemExit(f"FAIL: upstream notice/source has changed: {entry['path']}")
print(f"PASS: {len(notices)} checked upstream license/source hashes verified")

# Never silently reintroduce the removed headers into a release snapshot.
for name in ("command.h", "avr_cpunames.h"):
    if (vendor / name).exists():
        raise SystemExit(f"FAIL: removed upstream header reintroduced: {name}")
for name in ("src/command.h", "tools/baseline/avr_cpunames.h"):
    text = (root / name).read_text()
    if (
        "SPDX-License-Identifier: GPL-2.0-or-later" not in text
        or "Project-authored" not in text
    ):
        raise SystemExit(f"FAIL: project replacement notice missing: {name}")
print("PASS: project replacement notices and excluded upstream headers checked")
