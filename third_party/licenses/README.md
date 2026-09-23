# Toolchain runtime notices

The firmware links runtime support from the documented Arduino AVR toolchain
`7.3.0-atmel3.6.1-arduino7` (GCC 7.3.0, avr-libc 2.0.0).
The compiler itself is not included in this repository or release archive.

* `avr-libc-2.0.0-LICENSE.txt`: upstream avr-libc release license and attribution,
  from https://github.com/avrdudes/avr-libc/blob/avr-libc-2_0_0-release/LICENSE.
* `GCC-7.3.0-COPYING3` and `GCC-7.3.0-COPYING.RUNTIME`: GCC GPLv3 text and
  Runtime Library Exception 3.1, from the corresponding files at
  https://github.com/gcc-mirror/gcc/tree/releases/gcc-7.3.0.

These notices apply to their respective third-party components; they do not
replace the project's GPL-2.0-or-later license. Preserve these files when
redistributing compiled images. See individual upstream sources for detailed
copyright notices and [the provenance report](../../docs/THIRD_PARTY.md).

`GCC-AVR-NOTICE.txt` retains the copyright and exception notice from AVR libgcc.
`SOURCES.json` records checked upstream URLs and hashes. Project-wide scope and
distribution obligations are in [LICENSES.md](../../LICENSES.md).
