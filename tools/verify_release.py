"""Verify release hashes and rebuild HEX from the archive in a temporary directory."""

# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
build_dir = (root / "build").resolve()
with tempfile.TemporaryDirectory(prefix="release-check-", dir=build_dir) as temporary:
    dest = Path(temporary).resolve()
    if dest.parent != build_dir or not dest.name.startswith("release-check-"):
        raise SystemExit("Unexpected verification directory")
    with zipfile.ZipFile(root / "dist/mega2560_ota_bootloader.zip") as archive:
        prefix = "mega2560_ota_bootloader/"
        manifest = json.loads(archive.read(prefix + "SHA256SUMS.json"))
        for name, expected in manifest.items():
            target = (dest / prefix / name).resolve()
            if not target.is_relative_to(dest / prefix):
                raise SystemExit("Archive contains an unsafe path")
            data = archive.read(prefix + name)
            if hashlib.sha256(data).hexdigest() != expected:
                raise SystemExit(f"Archive hash mismatch: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    project = dest / "mega2560_ota_bootloader"
    for command in (("tools/check_sources.py",), ("tools/build.py", "final")):
        result = subprocess.run(
            [sys.executable, *command],
            cwd=project,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode:
            raise SystemExit(result.stdout.decode(errors="replace"))
    if (project / "build/final/bootloader.hex").read_bytes() != (
        root / "build/final/bootloader.hex"
    ).read_bytes():
        raise SystemExit("Rebuilt HEX differs from release")
    report = (
        "PASS: ZIP hashes, vendored source hashes, fresh AVR rebuild and identical HEX.\n"
        + result.stdout.decode(errors="replace")
    )
(root / "build/tests").mkdir(parents=True, exist_ok=True)
(root / "build/tests/release.txt").write_text(report)
print(report)
