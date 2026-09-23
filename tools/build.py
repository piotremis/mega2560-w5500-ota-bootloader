"""Reproducible AVR build, also used by Makefile (Python 3, no packages)."""

import os, pathlib, shutil, subprocess, sys, json, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)


def tool(name):
    prefix = os.environ.get("AVR_PREFIX", "")
    found = shutil.which(prefix + "avr-" + name)
    if found:
        return found
    candidates = list(
        (
            pathlib.Path.home()
            / "AppData/Local/Arduino15/packages/arduino/tools/avr-gcc"
        ).glob("*/bin/avr-" + name + ".exe")
    )
    if candidates:
        return str(sorted(candidates)[-1])
    raise SystemExit("Set PATH or AVR_PREFIX to AVR toolchain prefix")


def run(args):
    return subprocess.check_output(
        [str(x) for x in args], stderr=subprocess.STDOUT
    ).decode(errors="replace")


def build(stage="final"):
    out = pathlib.Path("build") / stage
    out.mkdir(parents=True, exist_ok=True)
    flags = [
        "-mmcu=atmega2560",
        "-DF_CPU=16000000UL",
        "-Os",
        "-fno-jump-tables",
        "-std=gnu11",
        "-ffunction-sections",
        "-fdata-sections",
        "-fstack-usage",
        "-Isrc",
        "-fdebug-prefix-map=" + str(ROOT) + "=.",
        "-fdebug-prefix-map=" + ROOT.as_posix() + "=.",
    ]
    toolchain_path = pathlib.Path(tool("gcc")).resolve().parent.parent
    for prefix in {str(toolchain_path), toolchain_path.as_posix()}:
        for spelling in {prefix, prefix.lower()}:
            flags.append("-fdebug-prefix-map=" + spelling + "=/avr-toolchain")
    if stage == "official":
        sources = ["third_party/arduino-stk500v2/stk500boot.c"]
        flags += ["-Dprog_char=const char", "-Itools/baseline"]
    else:
        sources = [str(p) for p in sorted(pathlib.Path("src").glob("*.c"))]
        flags += [
            "-g",
            "-mcall-prologues",
            "-fno-inline-small-functions",
            "-fno-tree-scev-cprop",
            "-flto",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-DSTAGE="
            + str(
                {
                    "serial": 2,
                    "w5500": 4,
                    "dhcp": 5,
                    "dns": 6,
                    "http": 7,
                    "eeprom": 8,
                    "stream": 9,
                    "crc": 10,
                    "recovery": 11,
                    "final": 12,
                }[stage]
            ),
        ]
    objects = []
    for source in sources:
        obj = out / (pathlib.Path(source).stem + ".o")
        objects.append(obj)
        compile_flags = (
            [f for f in flags if f not in ("-fstack-usage", "-flto")]
            if pathlib.Path(source).name == "early.c"
            else flags
        )
        print(run([tool("gcc"), *compile_flags, "-c", source, "-o", obj]), end="")
    elf = out / "bootloader.elf"
    script = [] if stage == "official" else ["-Wl,-T,linker/boot_assert.ld"]
    print(
        run(
            [
                tool("gcc"),
                *flags,
                "-save-temps",
                *objects,
                *script,
                "-Wl,--relax,--gc-sections,--section-start=.text=0x3e000,-Map="
                + str(out / "bootloader.map"),
                "-o",
                elf,
            ]
        ),
        end="",
    )
    # MAP paths are diagnostic only; use a stable logical toolchain root.
    map_file = out / "bootloader.map"
    map_text = map_file.read_text().replace("\\", "/")
    toolchain = pathlib.Path(tool("gcc")).resolve().parent.parent.as_posix()
    map_text = re.sub(re.escape(toolchain), "<avr-toolchain>", map_text, flags=re.I)
    map_text = re.sub(re.escape(ROOT.as_posix()) + "/", "", map_text, flags=re.I)
    map_file.write_text(map_text)
    # GCC 7 LTO emits temporary files into cwd.
    for p in list(ROOT.glob("bootloader.elf.ltrans*")) + list(
        ROOT.glob("bootloader.res")
    ):
        if p.is_file():
            p.replace(out / p.name)
    print(
        run(
            [
                tool("objcopy"),
                "-O",
                "ihex",
                "-R",
                ".eeprom",
                elf,
                out / "bootloader.hex",
            ]
        ),
        end="",
    )
    sections = run([tool("objdump"), "-h", elf])
    sizes = run([tool("size"), "-A", elf])
    symbols = run([tool("nm"), "-S", "--size-sort", elf])
    (out / "sections.txt").write_text(sections)
    (out / "symbols.txt").write_text(symbols)
    flash = 0
    end = 0x3E000
    ram = 0
    violations = []
    lines = sections.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"\s*\d+\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", line)
        if not m:
            continue
        name, size, vma, lma = m.groups()
        size, vma, lma = [int(x, 16) for x in (size, vma, lma)]
        if name in (".data", ".bss", ".noinit"):
            ram += size
        if (
            size
            and "ALLOC" in lines[i + 1]
            and "LOAD" in lines[i + 1]
            and lma < 0x800000
        ):
            if lma < 0x3E000 or lma + size > 0x40000:
                violations.append(f"{name} {lma:x}+{size}")
            flash += size
            end = max(end, lma + size)
    report = {
        "stage": stage,
        "flash_bytes": flash,
        "flash_end_exclusive": hex(end),
        "flash_free": 0x40000 - end,
        "static_sram_bytes": ram,
        "sram_before_stack": 8192 - ram,
    }
    (out / "size.txt").write_text(sizes + "\n" + json.dumps(report, indent=2) + "\n")
    (out / "size.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    if violations:
        raise SystemExit(
            "INVALID: Flash section outside boot: " + ", ".join(violations)
        )
    if flash > 8192 or end > 0x40000:
        raise SystemExit("INVALID: bootloader exceeds 8192 bytes")
    # Independently inspect Intel HEX addresses AND checksums (not file size).
    base = 0
    addresses = set()
    for line in (out / "bootloader.hex").read_text().splitlines():
        b = bytes.fromhex(line[1:])
        if sum(b) % 256 != 0 or len(b) != b[0] + 5:
            raise SystemExit("INVALID: Intel HEX record length/checksum")
        count, addr, kind = b[0], int.from_bytes(b[1:3], "big"), b[3]
        if kind == 4:
            base = int.from_bytes(b[4:6], "big") << 16
        elif kind == 2:
            base = int.from_bytes(b[4:6], "big") << 4
        elif kind == 0:
            for a in range(base + addr, base + addr + count):
                if not 0x3E000 <= a < 0x40000 or a in addresses:
                    raise SystemExit("INVALID: HEX address outside boot or duplicated")
                addresses.add(a)
    if not (
        len(addresses) == flash
        and min(addresses) == 0x3E000
        and max(addresses) + 1 == end
    ):
        raise SystemExit("INVALID: ELF and HEX address coverage differ")


if __name__ == "__main__":
    try:
        build(sys.argv[1] if len(sys.argv) > 1 else "final")
    except subprocess.CalledProcessError as e:
        print(e.output.decode(errors="replace"))
        sys.exit(e.returncode)
