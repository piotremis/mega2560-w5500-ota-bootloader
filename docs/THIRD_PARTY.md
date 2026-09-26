# Third-party provenance

[Documentation](README.md) / Provenance

[LICENSES.md](../LICENSES.md) is the authoritative project guide to license scope
and distribution requirements. This page records the engineering references and
which code was adapted. Original license texts and author notices are preserved.

## Reference projects

| Project | MCU scope | W5500 | Update mechanism | Role |
|---|---|---|---|---|
| Arduino STK500v2 | Includes ATmega2560 | No | UART/STK500v2 | Basis of the serial implementation |
| Athena | Includes ATmega2560 | Yes; W5100/5200/5500 variants | Ethernet TFTP and serial | SPI, reset, EEPROM and architecture reference |
| Ariadne, per1234 fork | ATmega2560 and others | No in inspected fork: W5100 | Ethernet TFTP and serial | Historical architecture reference |
| MicroBridge | ATmega2560 | No direct support | BIN from SD/FAT to Flash and serial | Page streaming and EEPROM flag reference |

The requested arduino/Ariadne-Bootloader URL was unavailable during the original
review. The [per1234 fork](https://github.com/per1234/Ariadne-Bootloader) was
inspected instead. These findings apply to the pinned revisions, not every fork.
MicroBridge is not a network HTTP client; no SD support was added to this project.

## Inspected revisions

| Source | Commit | License finding |
|---|---|---|
| [Arduino](https://github.com/arduino/Arduino-stk500v2-bootloader) | `06ebf3701162b7b7c557dd64bc10796507dbada5` | stk500boot.c: GPL-2.0-or-later; Peter Fleury and modification notices retained |
| [Athena](https://github.com/embeddedartistry/athena-bootloader) | `f2066e49dec5077999283cba0f7d801a0dd942f0` | Root LGPL-2.1; inspected spi.c/net.c/tftp.c headers state GPL-2.0; do not treat all files as LGPL |
| [Ariadne fork](https://github.com/per1234/Ariadne-Bootloader) | `ce0a5a23d3e8087cbb82be42424f779af0e42fd5` | README and spi.c indicate GPLv2 |
| [MicroBridge](https://github.com/FleetProbe/MicroBridge-Arduino-ATMega2560) | `1aaff1d4fb30c761da0df71cf404aad10e545a5e` | stk500boot.c GPL-2.0-or-later; pff.c/pff.h have separate Petit FatFs terms |
| [avrdude](https://github.com/avrdudes/avrdude) | `7a4c9a21eca02ee4fb251d4861c3b1b7732be378` | GPL-2.0-or-later; protocol reference/test tool only, not linked |

## Adapted code and architectural references

**Arduino:** The unchanged upstream C baseline builds to 5778 bytes, using a
`prog_char` compatibility alias and `-fno-jump-tables` instead of obsolete
`-mno-tablejump`. Its monitor produces legacy pointer/const warnings; this image
is for comparison, not installation. The final serial implementation adapts the
parser/dispatcher, removes the monitor, other MCUs and lock programming, and
replaces old timing and EEPROM addressing. `tools/derive_stk.py` extracts sign-on
and parameter cases. Shared page programming adds bounds checks and recovery.

**Athena:** The review covered ethernet spi.c, net.c, w5500.h, tftp.c, EEPROM
configuration and main.c. W5500 uses a control byte after the 16-bit SPI address
and separate register/buffer blocks. Shared SPI requires other chip selects to
be inactive. Athena's driver and TFTP code were not copied. The project driver
uses the [WIZnet register documentation](https://docs.wiznet.io/Product/Chip/Ethernet/W5500)
and implements only socket 0, VDM and required operations.

**Ariadne:** The inspected W5100 driver sends an opcode before the address,
unlike W5500. Only serial/network separation and memory organization informed
the design; no code or application reset-server component was copied.

**MicroBridge:** The review covered the EEPROM flag at `0x1FF == 0xF0`, opening
firmware.bin, page programming below `0x3E000`, FF padding and flag clearing.
This implementation uses an independent CRC record and durable PENDING until
verification. No FAT/SD code or unverified flag-clearing logic was copied.

The final image links project `src/` files and required AVR runtime code, not
large networking libraries from these reference projects.

## Included materials

The unchanged GPL-2.0-or-later `stk500boot.c` snapshot has its revision and SHA256
recorded in [third_party](../third_party/arduino-stk500v2/README.md). Reference
clones are not build dependencies or release contents. Athena, Ariadne,
MicroBridge and avrdude are not redistributed.

The project includes avr-libc 2.0.0 notices, GCC 7.3.0 GPLv3 and Runtime Library
Exception texts under `third_party/licenses/`. Compiler binaries are excluded.
Project-authored and adapted sources, tests, tools and documentation use
GPL-2.0-or-later; upstream materials retain their original terms.

## Header replacements and license review

Arduino, avr-libc and GCC texts were checked against pinned upstream sources
on 2026-09-18; [SOURCES.json](../third_party/licenses/SOURCES.json) records URLs
and hashes. On 2026-09-23, upstream command.h and avr_cpunames.h were removed
because their separate license grants were not established.

Project-authored replacements define only required wire identifiers in
`src/command.h` and one MCU label in `tools/baseline/avr_cpunames.h`.
Upstream comments, CPU-name tables and unused definitions were not transferred.
This does not assign a new license to the originals. `make official` still
compiles the unchanged upstream C file with these replacement support headers.

Version 1.0.0 starts a new Git history containing the reviewed tree. Removed
headers are absent from that history and release ZIP; this does not retroactively
relicense previously distributed copies. See [LICENSES.md](../LICENSES.md).
