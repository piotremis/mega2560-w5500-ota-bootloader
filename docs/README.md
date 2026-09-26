# Documentation

The bootloader targets ATmega2560 at 16 MHz with an 8 KiB boot section.
All project documentation is maintained in English.

| Guide | Use it to |
|---|---|
| [Build and installation](INSTALL.md) | Build, wire and program through ISP; upload applications through CH340 |
| [EEPROM and application API](EEPROM.md) | Provision identity/network settings and request OTA safely |
| [OTA protocol](OTA.md) | Configure the update server and understand network/recovery behavior |
| [STK500v2 compatibility](STK500.md) | Check command support and avrdude integration |
| [Validation](TESTING.md) | Distinguish host tests, hardware tests and remaining acceptance work |
| [Memory report](SIZE.md) | Inspect measured Flash/SRAM usage and integration stages |
| [Third-party provenance](THIRD_PARTY.md) | Trace adaptations and reference projects |
| [Release process](RELEASING.md) | Build and verify a matching-source distribution |

Start with the [project README](../README.md). Contributors should also read
[CONTRIBUTING.md](../CONTRIBUTING.md). License scope and distribution requirements
are maintained in [LICENSES.md](../LICENSES.md); original license texts and notices
are preserved under `third_party/` and in [LICENSE](../LICENSE).
