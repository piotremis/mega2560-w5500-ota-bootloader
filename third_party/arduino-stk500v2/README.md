# Arduino STK500v2 source snapshot

Upstream: https://github.com/arduino/Arduino-stk500v2-bootloader

Commit: `06ebf3701162b7b7c557dd64bc10796507dbada5`.
Only `stk500boot.c` is retained as unmodified upstream source for `make official`
and derivation provenance. SHA256SUMS.json records its original bytes.
`stk500boot.c` is GPL-2.0-or-later; retain its copyright and modification notices.
The upstream `command.h` and `avr_cpunames.h` are not distributed: their file-level
license grants were not established. The reference build uses project-authored
`src/command.h` (wire constants) and `tools/baseline/avr_cpunames.h` (one MCU name).
The C source is unchanged; these support headers are replacements, so this target
is an upstream-source baseline, not a byte-for-byte copy of the complete upstream
build environment. See ../../LICENSES.md. Do not format the retained C snapshot.
