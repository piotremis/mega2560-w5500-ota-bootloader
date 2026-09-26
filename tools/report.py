"""Attribute actual final .text instructions using DWARF (works with LTO)."""

from build import ROOT, tool, run
import re, subprocess, json, collections, pathlib

out = pathlib.Path("build/final")
elf = out / "bootloader.elf"
dis = run([tool("objdump"), "-d", elf])
(out / "disassembly.txt").write_text(dis)
ins = []
for line in dis.splitlines():
    m = re.match(r"\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)", line)
    if m:
        ins.append((int(m[1], 16), len(m[2].split())))
locations = (
    subprocess.check_output(
        [tool("addr2line"), "-e", str(elf)],
        input="".join(f"{a:x}\n" for a, n in ins).encode(),
    )
    .decode()
    .splitlines()
)
assert len(locations) == len(ins)
categories = {
    "stk500.c": "STK500v2",
    "arduino_cases.inc": "STK500v2",
    "w5500.c": "W5500",
    "dhcp.c": "DHCP",
    "dns.c": "DNS",
    "http.c": "HTTP",
    "url_parse.h": "HTTP",
    "ota.c": "OTA",
    "eeprom_cfg.c": "EEPROM",
    "network_cfg.c": "EEPROM",
    "crc32.c": "CRC32",
}
counts = collections.Counter()
detail = []
for (a, n), loc in zip(ins, locations):
    filename = re.split(r"[/\\]", loc.rsplit(":", 1)[0])[-1]
    cat = categories.get(filename, "Other")
    counts[cat] += n
    detail.append(f"{a:05x}\t{n}\t{cat}\t{loc}")
size = json.loads((out / "size.json").read_text())
counts["Other"] += size["flash_bytes"] - sum(counts.values())
assert sum(counts.values()) == size["flash_bytes"]
(out / "attribution.tsv").write_text("\n".join(detail) + "\n")
(out / "modules.json").write_text(json.dumps(counts, indent=2))
table = (
    "| Component | Bytes |\n|---|---:|\n"
    + "".join(
        f"| {k} | {counts[k]} |\n"
        for k in (
            "STK500v2",
            "W5500",
            "DHCP",
            "DNS",
            "HTTP",
            "OTA",
            "EEPROM",
            "CRC32",
            "Other",
        )
    )
    + f"| **TOTAL** | **{sum(counts.values())}** |\n| LIMIT | 8192 |\n"
)
stages = (
    "| Stage | Flash bytes | Static SRAM bytes | Flash end (exclusive) |\n|---|---:|---:|---|\n"
)
for s in (
    "official",
    "serial",
    "w5500",
    "dhcp",
    "dns",
    "http",
    "eeprom",
    "stream",
    "crc",
    "recovery",
    "final",
):
    p = ROOT / "build" / s / "size.json"
    if p.exists():
        d = json.loads(p.read_text())
        stages += f"| {s} | {d['flash_bytes']} | {d['static_sram_bytes']} | {d['flash_end_exclusive']} |\n"
doc = (
    "# Memory report\n\n[Documentation](README.md) / Memory\n\n"
    + table
    + "\nInstruction attribution uses DWARF information from the final ELF. LTO moves and merges code; these are attributed address ranges, not independently linked library sizes. Other includes startup, the AVR platform, libc/libgcc, data initializers and padding. Every byte is counted once. Details: `build/final/attribution.tsv`.\n\n"
    + stages
)
doc += "\nStage rows are included only when their local size reports exist. Run `make official` and `make stages` before this report for the full comparison. Only the final image is intended for installation.\n"
doc += "\nAttribution follows source files: CRC32 includes the range_ok helper. OTA covers streaming and verification; shared SPM code in platform.c is counted under Other because serial programming also uses it.\n"
doc += "\nEarly builds exceeded the limit: HTTP without shared prologues used 8284 bytes (92 over), and streaming before LTO used 8272 bytes (80 over). Shared prologues and LTO reduced size without removing required features. Recovery was integrated with EEPROM/SPM; its measurement stage adds no artificial code. Install only `build/final/bootloader.hex`.\n"
doc += f"\nFinal: {size['flash_bytes']} bytes, last occupied address `0x{int(size['flash_end_exclusive'], 16) - 1:05X}`, {size['flash_free']} bytes of free Flash. Static SRAM: {size['static_sram_bytes']} bytes; {size['sram_before_stack']} bytes remain before stack use. See [validation](TESTING.md) for stack considerations.\n"
(ROOT / "docs/SIZE.md").write_text(doc, encoding="utf-8")
print(table)
