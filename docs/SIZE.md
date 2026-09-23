# Wynik pomiarów

| Element | Bytes |
|---|---:|
| STK500v2 | 1256 |
| W5500 | 1278 |
| DHCP | 956 |
| DNS | 1010 |
| HTTP | 1124 |
| OTA | 272 |
| EEPROM | 334 |
| CRC32 | 184 |
| inne | 1532 |
| **TOTAL** | **7946** |
| LIMIT | 8192 |

Rozliczenie rzeczywistych instrukcji finalnego ELF według informacji DWARF. LTO przenosi i scala kod; to atrybucja adresów, nie suma niezależnie linkowanych bibliotek. `inne` obejmuje startup, platformę AVR, libc/libgcc, inicjalizatory `.data` i padding. Każdy bajt policzono raz. Szczegóły: `build/final/attribution.tsv`.

| Etap | Flash B | statyczny SRAM B | koniec wyłączny |
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

Atrybucja jest według plików: CRC32 obejmuje również helper `range_ok` umieszczony w crc32.c. OTA obejmuje logikę strumieniowania/weryfikacji; wspólne instrukcje SPM z platform.c są w `inne`, ponieważ służą też STK500v2.

Wczesne buildy przekroczyły limit: HTTP bez współdzielonych prologów 8284 B (92 B ponad limit), streaming przed LTO 8272 B (80 B ponad limit). Zastosowano `-mcall-prologues`, następnie LTO, zachowując funkcje. Tabela pokazuje ponownie zmierzone etapy z finalnymi flagami. Recovery wdrożono już przy integracji EEPROM/SPM; etap recovery potwierdza istniejący mechanizm i nie dodaje sztucznego przyrostu kodu. Buildy pośrednie są tylko pomiarowe; do instalacji służy wyłącznie `build/final/bootloader.hex`.

Final: 7946 B, ostatni zajęty adres `0x3FF09`, 246 B wolnego Flash. Statyczny SRAM 1205 B; 6987 B pozostaje przed uwzględnieniem stosu.
