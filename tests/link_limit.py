"""Negative linker test: deliberately oversize .text and .data must fail."""

import sys, pathlib, subprocess

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from build import ROOT, tool

out = ROOT / "build/tests"
out.mkdir(exist_ok=True)
for section in (".text", ".data"):
    src = out / "oversize.S"
    obj = out / "oversize.o"
    src.write_text(f".section {section}\n.global main\nmain:\n.space 8193,1\n")
    subprocess.run(
        [tool("gcc"), "-mmcu=atmega2560", "-c", str(src), "-o", str(obj)], check=True
    )
    p = subprocess.run(
        [
            tool("gcc"),
            "-mmcu=atmega2560",
            str(obj),
            "-Wl,--section-start=.text=0x3e000,-T,linker/boot_assert.ld",
            "-o",
            str(out / "invalid.elf"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert p.returncode != 0 and b"exceeds 8 KiB" in p.stdout, p.stdout
(out / "link-limit.txt").write_text(
    "PASS: oversized .text and Flash initializers of .data rejected by linker.\n"
)
print("PASS: negative linker size tests")
