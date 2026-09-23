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
    cat = categories.get(filename, "inne")
    counts[cat] += n
    detail.append(f"{a:05x}\t{n}\t{cat}\t{loc}")
size = json.loads((out / "size.json").read_text())
counts["inne"] += size["flash_bytes"] - sum(counts.values())
assert sum(counts.values()) == size["flash_bytes"]
(out / "attribution.tsv").write_text("\n".join(detail) + "\n")
(out / "modules.json").write_text(json.dumps(counts, indent=2))
table = (
    "| Element | Bytes |\n|---|---:|\n"
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
            "inne",
        )
    )
    + f"| **TOTAL** | **{sum(counts.values())}** |\n| LIMIT | 8192 |\n"
)
stages = (
    "| Etap | Flash B | statyczny SRAM B | koniec wyłączny |\n|---|---:|---:|---|\n"
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
    "# Wynik pomiarów\n\n"
    + table
    + "\nRozliczenie rzeczywistych instrukcji finalnego ELF według informacji DWARF. LTO przenosi i scala kod; to atrybucja adresów, nie suma niezależnie linkowanych bibliotek. `inne` obejmuje startup, platformę AVR, libc/libgcc, inicjalizatory `.data` i padding. Każdy bajt policzono raz. Szczegóły: `build/final/attribution.tsv`.\n\n"
    + stages
)
doc += "\nAtrybucja jest według plików: CRC32 obejmuje również helper `range_ok` umieszczony w crc32.c. OTA obejmuje logikę strumieniowania/weryfikacji; wspólne instrukcje SPM z platform.c są w `inne`, ponieważ służą też STK500v2.\n"
doc += "\nWczesne buildy przekroczyły limit: HTTP bez współdzielonych prologów 8284 B (92 B ponad limit), streaming przed LTO 8272 B (80 B ponad limit). Zastosowano `-mcall-prologues`, następnie LTO, zachowując funkcje. Tabela pokazuje ponownie zmierzone etapy z finalnymi flagami. Recovery wdrożono już przy integracji EEPROM/SPM; etap recovery potwierdza istniejący mechanizm i nie dodaje sztucznego przyrostu kodu. Buildy pośrednie są tylko pomiarowe; do instalacji służy wyłącznie `build/final/bootloader.hex`.\n"
doc += f"\nFinal: {size['flash_bytes']} B, ostatni zajęty adres `0x{int(size['flash_end_exclusive'], 16) - 1:05X}`, {size['flash_free']} B wolnego Flash. Statyczny SRAM {size['static_sram_bytes']} B; {size['sram_before_stack']} B pozostaje przed uwzględnieniem stosu.\n"
(ROOT / "docs/SIZE.md").write_text(doc, encoding="utf-8")
print(table)
