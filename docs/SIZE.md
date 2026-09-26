# Memory report

[Documentation](README.md) / Memory

| Component | Bytes |
|---|---:|
| STK500v2 | 1256 |
| W5500 | 1278 |
| DHCP | 956 |
| DNS | 1010 |
| HTTP | 1124 |
| OTA | 272 |
| EEPROM | 334 |
| CRC32 | 184 |
| Other | 1532 |
| **TOTAL** | **7946** |
| LIMIT | 8192 |

Instruction attribution uses DWARF information from the final ELF. LTO moves and merges code; these are attributed address ranges, not independently linked library sizes. Other includes startup, the AVR platform, libc/libgcc, data initializers and padding. Every byte is counted once. Details: `build/final/attribution.tsv`.

| Stage | Flash bytes | Static SRAM bytes | Flash end (exclusive) |
|---|---:|---:|---|
| official | 5778 | 18 | 0x3f692 |
| serial | 2228 | 893 | 0x3e8b4 |
| w5500 | 2510 | 1053 | 0x3e9ce |
| dhcp | 4202 | 1077 | 0x3f06a |
| dns | 5792 | 1089 | 0x3f6a0 |
| http | 7120 | 1205 | 0x3fbd0 |
| eeprom | 7574 | 1205 | 0x3fd96 |
| stream | 7822 | 1205 | 0x3fe8e |
| crc | 7946 | 1205 | 0x3ff0a |
| recovery | 7946 | 1205 | 0x3ff0a |
| final | 7946 | 1205 | 0x3ff0a |

Stage rows are included only when their local size reports exist. Run `make official` and `make stages` before this report for the full comparison. Only the final image is intended for installation.

Attribution follows source files: CRC32 includes the range_ok helper. OTA covers streaming and verification; shared SPM code in platform.c is counted under Other because serial programming also uses it.

Early builds exceeded the limit: HTTP without shared prologues used 8284 bytes (92 over), and streaming before LTO used 8272 bytes (80 over). Shared prologues and LTO reduced size without removing required features. Recovery was integrated with EEPROM/SPM; its measurement stage adds no artificial code. Install only `build/final/bootloader.hex`.

Final: 7946 bytes, last occupied address `0x3FF09`, 246 bytes of free Flash. Static SRAM: 1205 bytes; 6987 bytes remain before stack use. See [validation](TESTING.md) for stack considerations.
