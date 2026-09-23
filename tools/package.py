"""Archive the reproducible project, excluding compiler caches and cloned .git dirs."""

import pathlib, zipfile, hashlib, json, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "tools/check_sources.py")], check=True)
out = ROOT / "dist"
out.mkdir(exist_ok=True)
target = out / "mega2560_ota_bootloader.zip"
files = []
for folder in (
    "src",
    "application",
    "tools",
    "tests",
    "docs",
    "linker",
    "third_party",
    ".github",
):
    files += [
        p
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
files += [
    ROOT / "README.md",
    ROOT / "VERSION",
    ROOT / "CHANGELOG.md",
    ROOT / "Makefile",
    ROOT / "build.ps1",
    ROOT / "buildAndProgram.ps1",
    ROOT / "LICENSE",
    ROOT / "LICENSES.md",
    ROOT / "README.pl.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / ".gitignore",
    ROOT / ".gitattributes",
    ROOT / ".editorconfig",
    ROOT / ".clang-format",
]
# Release artifacts are explicit: never publish device records, private logs,
# toolchains or intermediate integration-stage images.
for name in (
    "bootloader.elf",
    "bootloader.hex",
    "bootloader.map",
    "size.txt",
    "size.json",
    "sections.txt",
    "symbols.txt",
    "modules.json",
):
    artifact = ROOT / "build/final" / name
    if not artifact.is_file():
        raise SystemExit(f"Missing release artifact: {artifact}; run build first")
    files.append(artifact)
# Fail closed if a release file leaks this machine's home/workspace paths.
# Normalize separators and case for Windows paths, including binary DWARF strings.
private_roots = [str(ROOT), str(pathlib.Path.home())]
for path in files:
    data = path.read_bytes().replace(b"\\", b"/").lower()
    for private_root in private_roots:
        needle = private_root.replace("\\", "/").lower().encode()
        if needle in data:
            raise SystemExit(
                f"Private local path in release file: {path.relative_to(ROOT)}"
            )
manifest = {
    str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
        p.read_bytes()
    ).hexdigest()
    for p in sorted(set(files))
}
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in manifest:
        z.write(ROOT / name, "mega2560_ota_bootloader/" + name)
    z.writestr(
        "mega2560_ota_bootloader/SHA256SUMS.json", json.dumps(manifest, indent=2)
    )
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    for name, digest in manifest.items():
        assert (
            hashlib.sha256(z.read("mega2560_ota_bootloader/" + name)).hexdigest()
            == digest
        )
(out / "SHA256SUMS.txt").write_text(
    hashlib.sha256(target.read_bytes()).hexdigest() + "  " + target.name + "\n"
)
print(
    f"{target}: {target.stat().st_size} bytes, {len(manifest)} files; ZIP CRC and SHA256 verified"
)
