# Mega2560 Ethernet OTA bootloader

**Version 1.0.0** · [Changelog](CHANGELOG.md)

[Documentation](docs/README.md) · [Installation](docs/INSTALL.md) · [Licenses](LICENSES.md)

Bare-metal C bootloader for **ATmega2560, 16 MHz**, based on Arduino STK500v2.
It supports normal Arduino Mega uploads over UART0/CH340 and application-requested
OTA via **W5500 → HTTP GET → raw BIN → Flash → CRC32 + readback**.

**Current build:** 7946 / 8192 bytes Flash, 246 bytes free; 1205 bytes static SRAM.
The boot image occupies `0x3E000–0x3FF09`. The build checks ELF load addresses and
HEX checksums/range. [Full memory report](docs/SIZE.md).

**Validation:** AVR build and host tests pass. Both UART0/CH340 upload and W5500 OTA
were successfully tested on hardware on 2026-09-22.
Power-loss and fault-injection tests remain unconfirmed; see [test scope](docs/TESTING.md).
CRC32 is integrity checking, not authentication.

## Build on Windows

Install Python 3.9+ and the Arduino AVR toolchain (tested:
`7.3.0-atmel3.6.1-arduino7`). The scripts detect Arduino15 tools; GNU make is not
needed. For host tests, download Zig once:

```powershell
python -m pip download ziglang==0.13.0 --dest build/tool-download
.\build.ps1
```

Run in the project directory. Output: `build/final/bootloader.hex`, `.elf`, `.map`
and size reports. Use `-Python C:\path\python.exe` to select an interpreter.
`-SkipTests` skips host tests but keeps all build/size checks.

## Install through AVRISP mkII USB

Connect the programmer to the target's ICSP and provide target power. Installation
**erases the application and may erase EEPROM**. Assign a unique decimal S/N:

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001
```

The script builds/tests, checks the MCU signature, sets fuses, writes and verifies
EEPROM and Flash, then protects the boot section. Errors stop the sequence.
To build and preview commands without accessing hardware:

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001 -DryRun
```

S/N `0001` creates MAC `02:53:49:4F:00:01`; `0002` creates `02:53:49:4F:00:02`.
Factory EEPROM is **IDLE**, DHCP with fallback **192.168.1.50/24**; gateway/DNS
are **192.168.1.1** (override with `-Gateway` / `-Dns`). S/N range: 1–65535.
All units share the fallback IP, so avoid simultaneous fallback on one subnet.
Device files are generated under `build/provision/`; do not publish them.

After ISP, use the standard **Arduino Mega 2560** board selection to upload the
application through CH340. Bootloader replacement always requires ISP.
See [installation](docs/INSTALL.md) for pins, fuses and troubleshooting.

## OTA and EEPROM

* W5500 CS: **D53/PB0**, configurable in [board_pins.h](src/board_pins.h).
  SPI: D52/SCK, D51/MOSI, D50/MISO. No SD support.
* One EEPROM record: **160 bytes at 0x0F60**, format v1, shared CRC, serial/MAC,
  network settings and OTA metadata. No automatic creation or migration.
* Network modes: **0 DHCP**, **1 DHCP then static fallback**, **2 forced static**.
  A literal IPv4 URL skips DNS; a hostname uses DNS A.
* The application preserves provisioned identity/network fields, writes image
  size/CRC/version/URL, commits PENDING and resets. Boot never searches for updates.
* HTTP 200 and matching Content-Length are required. Flash is streamed in
  256-byte pages, bounded below `0x3E000`. PENDING persists until both CRC checks pass.
* Missing/invalid metadata disables OTA without rewriting EEPROM. Recognized
  PENDING/ARMING blocks application boot even with damaged metadata.

No TLS, firmware signatures, rollback, HTTP server or bootloader self-update.
See [OTA protocol](docs/OTA.md) and [EEPROM/API](docs/EEPROM.md).

## Project map

| Directory | Purpose |
|---|---|
| `src/`, `linker/` | Firmware and hard Flash boundary assertions |
| `application/` | Application-side OTA request API |
| `tools/`, `tests/` | Build, provisioning, packaging and host tests |
| `docs/` | Installation, EEPROM, OTA, protocol, testing and size |
| `third_party/` | Pinned Arduino baseline and runtime license notices |

[Developer workflow](CONTRIBUTING.md) · [Release packaging](docs/RELEASING.md) ·
[STK500v2](docs/STK500.md) · [Tests](docs/TESTING.md) · [Reference analysis](docs/THIRD_PARTY.md)

Project-authored and adapted code: **GPL-2.0-or-later**, see [LICENSE](LICENSE).
Third-party notices and redistribution details: [LICENSES.md](LICENSES.md).
