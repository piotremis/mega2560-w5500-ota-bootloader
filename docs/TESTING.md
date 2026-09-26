# Validation and test scope

[Documentation](README.md) / Validation

## Evidence summary

| Layer | Evidence |
|---|---|
| Compilation | AVR-GCC 7.3.0; ATmega2560/16 MHz; warnings treated as errors for final sources; ELF/HEX/MAP and size checks |
| Static review | SPM bounds, 32-bit addresses, EEPROM policy and parser review; disassembly and ELF load addresses; not a formal proof |
| Host models | Production C with substituted hardware I/O; CRC, URL, HTTP, DNS, DHCP, EEPROM, Flash, OTA and STK tests |
| Protocol integration | Real avrdude 8.0-arduino.1 wiring upload/verify of 248 KiB Flash and 4 KiB EEPROM through a host UART/TCP model |
| Driver model | Production W5500 driver with SPI/register/socket/ring-buffer model |
| Hardware | UART0/CH340 upload and W5500 OTA tested successfully on 2026-09-22; earlier ISP testing verified an 8122-byte revision and fuse/lock settings |
| Release archive | ZIP checksums and source hashes verified; rebuild in a fresh directory produced identical HEX |

Host tests do not emulate AVR instructions or replace measurement of SPI, SPM,
clock timing, auto-reset, PHY/link behavior or brown-out. A successful build is
not hardware acceptance. Ordinary upload and OTA operation are hardware-tested;
power-loss, fault-injection and boundary acceptance remain separate work.

## Run software checks

Use `./build.ps1` on Windows, or `make all` followed by `make test` with the
required tools installed. [Installation](INSTALL.md) lists dependencies.

| Check | Coverage |
|---|---|
| `tools/check_sources.py` | Pinned Arduino source, license/source hashes, replacement-header notices and excluded upstream headers |
| `tests/run.py` | 27 test groups; production parsers, serial framing, update policy and recovery |
| `tests/w5500.py` | Default D53 and alternate CS; GPIO states, MAC, sockets, UDP framing, RX/TX wrap and timeouts |
| `tests/link_limit.py` | Deliberately oversized text and data initializers must fail linking |
| `tests/application_build.py` | C and C++ callers linked against C API objects; cfg_load, CRC, request and watchdog example |
| `tools/verify_release.py` | Archive hashes, source integrity, fresh AVR build and identical HEX |

Parser tests include over 2000 deterministic fuzz packets, every truncation of
sample DHCP/DNS replies, CRC against zlib, URL/port validation, HTTP lengths and
overflow. EEPROM tests cover 256 boot-state values, interruption at every write
while preparing a request from blank/IDLE records, PENDING/ARMING preservation,
factory identity mapping, and invalid metadata without automatic writes.
Invalid URLs must be rejected before any EEPROM write; valid URLs remain intact.

End-to-end models cover DHCP -> DNS -> HTTP -> Flash -> CRC with images of
1, 255, 256, 257, 700 and 253952 bytes, including 17-byte receive fragments.
Cases include CRC/readback failure, interruption after two pages and retry,
404, missing/duplicate/mismatched Content-Length, chunking, truncated body,
unavailable DHCP/DNS, IPv4 without DNS, ports 80/8080, forced static IP and fallback.
Tests inspect the destination address, port and Host header. Numeric-prefix
hostnames still use DNS; IPv4 accepts decimal leading zeroes and rejects bad octets.

STK tests exercise commands, frame checksum/token/length/sequence and `!!!` without
monitor activation. The W5500 model checks 2048-byte ring and 65536-byte pointer
wrap, oversized datagrams, SEND timeout, stuck commands, hardware SS as output,
CS active-low during each SPI byte and preservation of unrelated GPIO bits.

Run `python tests/avrdude.py` separately on Windows with Arduino15 avrdude installed,
after `tests/run.py`. It uses loopback rather than a COM port and does not access
a device. Logs and traces are written under `build/tests/`.

On Linux, `-Wl,-Bsymbolic` binds model symbols locally so the firmware's two-argument
`crc32()` cannot resolve to zlib's incompatible C ABI. The test deliberately loads
zlib globally to exercise this condition. This flag does not affect AVR firmware.
See [GNU ld options](https://sourceware.org/binutils/docs/ld/Options.html).
CI enables Python faulthandler and prints partial logs after failure. It also
builds with pinned AVR-GCC, checks bounds and rebuilds the release archive.

## SRAM and stack

Static SRAM is 1205 bytes: 160 bytes of `.data` and 1045 bytes of `.bss`.
The largest objects are the 600-byte packet buffer, 256-byte Flash page/HTTP line
buffer and 160-byte Config (including URL). W5500 buffers are controller memory.
The bootloader uses no heap allocation, VLAs, recursion or interrupts.

6987 bytes remain before stack use. GCC 7 LTO emits frame information in
`build/final/bootloader.elf.ltrans0.ltrans.su`; source-level `.su` files may be empty.
These frames alone do not prove maximum stack depth. A hypothetical 512-byte
stack budget leaves 6475 bytes, but this is not a measured high-water mark.
Measure stack watermark in a diagnostic hardware build before deployment.

## Hardware acceptance checklist

Successful UART upload and ordinary W5500 OTA do not imply completion of every
case below. Record board/module model, fuses, voltage, toolchain, HEX hash,
avrdude output, server logs/packet capture and result for each case.

| Test | Acceptance criterion |
|---|---|
| ISP/fuses/lock | Boot-only ELF/HEX; HFUSE D8; correct clock/lock; startup at 0x3E000 |
| CH340 upload | Auto-reset, sign-on, small and >128 KiB sketches, verify and application startup |
| UART EEPROM | Read/write low and high addresses; application honors reserved record |
| W5500 SPI | D53/PB0 CS; hardware SS output; VERSIONR=4; valid waveforms |
| Ordinary OTA | DHCP, DNS, HTTP, download/readback CRC, IDLE and application startup |
| Reset during OTA | Reset in every phase and first/middle/last page; PENDING and restart from zero |
| Power loss | Repeated cuts during EEPROM commit, SPM and verification; no partial application startup |
| Bad CRC/readback | Error LED, retained PENDING, no application jump |
| Image >253952 bytes | Reject before programming; boot unchanged |
| Image exactly 253952 bytes | 992 pages, last at 0x3DF00; correct CRC and boot unchanged |
| DNS unavailable | Timeout/retry; no partial application startup; UART recovery available |
| HTTP unavailable/link down | Timeout/retry and retained PENDING |
| HTTP 404/missing length | Fail before first SPM write |
| Truncated body | Fail, retry, preserve PENDING |
| Long transfer | Correct >64 KiB operation and repeated RX/TX wrap |
| Stack/power | Measure watermark and VCC/BOD/supervisor behavior during voltage drops |
| Boot protection | Compare ISP boot checksums before/after, including invalid UART addresses |

A full production acceptance claim requires completion of the applicable checklist.
