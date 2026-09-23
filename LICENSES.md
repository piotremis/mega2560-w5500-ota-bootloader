# License and attribution

The project-authored firmware, application helpers, tests, tools and documentation
are licensed under **GPL-2.0-or-later**. The full GPL version 2 text is in
[LICENSE](LICENSE). Original third-party files retain their own notices.
This is an independent project derived from Arduino STK500v2, not an official
Arduino or WIZnet release.

## Code included in the project or linked image

| Component | Applicable terms | Where used / notices |
|---|---|---|
| Arduino STK500v2, Peter Fleury and subsequent contributors | GPL-2.0-or-later, stated in `stk500boot.c` | Adapted serial dispatcher/framing in `src/stk500.c`, cases in `src/arduino_cases.inc`; original [notice](docs/ARDUINO-NOTICE.txt) and [pinned snapshot](third_party/arduino-stk500v2/README.md) |
| Project protocol constants and baseline MCU label | GPL-2.0-or-later | `src/command.h` is a newly written minimal enum of wire identifiers; `tools/baseline/avr_cpunames.h` defines only the ATmega2560 label. These are project files, not relicensed copies of the upstream headers. |
| avr-libc 2.0.0 | Modified BSD; retain copyright, conditions and disclaimer in source/binary distributions; no endorsement | Linked AVR runtime, libc functions and header macros. [License](third_party/licenses/avr-libc-2.0.0-LICENSE.txt), [header notices](third_party/licenses/avr-libc-header-notices.txt) |
| GCC 7.3.0 AVR libgcc | GPL-3.0-or-later with GCC Runtime Library Exception 3.1 | Linked arithmetic/prologue helpers. [GPLv3](third_party/licenses/GCC-7.3.0-COPYING3), [exception](third_party/licenses/GCC-7.3.0-COPYING.RUNTIME), [runtime notice](third_party/licenses/GCC-AVR-NOTICE.txt) |

The GCC exception permits eligible compiled combinations under the independent
modules' applicable terms; it does not relicense project sources or unrelated
third-party code. The included toolchain notices apply to the measured Arduino
AVR-GCC `7.3.0-atmel3.6.1-arduino7` build. Recheck runtime notices if changing it.

Primary evidence: the [Arduino source license header](https://github.com/arduino/Arduino-stk500v2-bootloader/blob/06ebf3701162b7b7c557dd64bc10796507dbada5/stk500boot.c),
[avr-libc 2.0.0 license](https://github.com/avrdudes/avr-libc/blob/avr-libc-2_0_0-release/LICENSE),
[GCC AVR runtime source](https://github.com/gcc-mirror/gcc/blob/releases/gcc-7.3.0/libgcc/config/avr/lib1funcs.S)
and [runtime exception](https://github.com/gcc-mirror/gcc/blob/releases/gcc-7.3.0/COPYING.RUNTIME).
Checked upstream texts and local hashes are recorded in
[SOURCES.json](third_party/licenses/SOURCES.json).

## Removed upstream headers (2026-09-23)

The pinned upstream `command.h` and `avr_cpunames.h` do not contain separate
license grants. Rather than infer permission or attach a new license to someone
else's files, both originals were removed from the current source tree and ZIP.
The protocol identifiers required for interoperability are expressed in a small
project-authored enum, without the upstream comments, tables or unused commands.
The protocol reference is [Microchip AVR068](https://ww1.microchip.com/downloads/en/Appnotes/doc2591.pdf),
sections 3 and 5; that document is linked, not redistributed. The monitor baseline
needs only one literal MCU label. The GPL-licensed Arduino C source and all its
copyright and modification notices are still included unchanged.

Version 1.0.0 starts a new Git history containing only the reviewed tree. The
removed headers are absent from that history and the release ZIP. Previously
distributed development copies are not retroactively relicensed by this change.

## Distributing a modified version or binaries

* Preserve copyright, license and warranty notices; identify modified files and
  the date of changes, as required by GPLv2 section 2(a).
* Supply recipients with the applicable license texts. For distribution of a
  GPL-covered derived work, comply with the GPL's source/distribution terms.
* When publishing HEX/ELF files, publish the matching source and build scripts
  alongside them using the supplied ZIP workflow (GPLv2 section 3(a)), rather
  than offering a binary alone. Include the runtime notices in that release.
* Do not claim hardware validation beyond the tests actually performed.

Consult [LICENSE](LICENSE), particularly sections 1–3, for the binding terms.
The archive includes source and build scripts but not a compiler toolchain.

## References not distributed

Athena, Ariadne and MicroBridge were architectural references. Their Ethernet,
TFTP and SD/FAT implementations were not copied into this project. Their full
repositories are not part of the source or release archive; no LGPL/Petit FatFs
license is added as if those components were linked here. The examined revisions
and file-level license findings are in [THIRD_PARTY.md](docs/THIRD_PARTY.md).

avrdude, Python, Zig, clang-format and Ruff are external development tools. Their
binaries and caches are not redistributed in this project. This distinction does
not exclude avr-libc/libgcc code that is actually linked into the firmware.
