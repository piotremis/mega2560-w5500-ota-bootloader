# Changelog

## 1.0.0 — 2026-09-23

Initial release for ATmega2560 at 16 MHz, with an 8 KiB boot section.

- Arduino-compatible UART0/CH340 upload using STK500v2.
- W5500 HTTP client OTA, DHCP, static fallback/forced static IP, DNS and IPv4 URLs.
- Streaming BIN programming, CRC32 plus Flash readback, EEPROM pending state.
- Factory provisioning, configurable W5500 CS (default D53), C/C++ application API.
- Pinned AVR build, size guards, host tests and reproducible release packaging.

Flash: 7946/8192 bytes; static SRAM: 1205 bytes. UART upload and W5500 OTA
have been tested on hardware. Power-loss and fault-injection acceptance remain
unconfirmed; see [test scope](docs/TESTING.md). CRC32 does not authenticate firmware.

This release starts a new Git history containing only the reviewed source tree.
EEPROM format remains 1; the release version does not change its layout or add
migration from earlier development layouts.
