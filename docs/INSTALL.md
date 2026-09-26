# Build and installation

[Documentation](README.md) / Installation

## Requirements

Target: ATmega2560, 16 MHz, 8 KiB boot section. Install Python 3.9+,
PowerShell, Arduino AVR-GCC `7.3.0-atmel3.6.1-arduino7` (including avr-libc
and binutils), and avrdude `8.0.0-arduino1`. A different compiler may change
firmware size. Windows scripts detect tools under `%LOCALAPPDATA%/Arduino15`;
set `AVR_PREFIX` to a tool directory such as `C:/avr/bin/` to override detection.
GNU make is optional on Windows. Run commands from the repository root.

Download the host-test compiler once, then build:

```powershell
python -m pip download ziglang==0.13.0 --dest build/tool-download
.\build.ps1
```

On Linux, with the AVR tools and a native C compiler on PATH:

```sh
make all
make test
```

The build produces ELF, HEX, MAP and reports in `build/final/`. It rejects
Flash load addresses outside `0x3E000–0x3FFFF`. Each invocation recompiles the
sources. Do not run concurrent builds: GCC LTO uses shared temporary filenames.
Only install `build/final/bootloader.hex`; intermediate stages are measurements.

## Wiring

Connect AVRISP mkII to the target ICSP: RESET, MOSI, MISO, SCK, GND and VTG.
Supply target power separately; do not assume the programmer supplies it.
Initial installation and bootloader replacement require ISP. CH340 is used for
subsequent application uploads.

| W5500 signal | Mega2560 pin |
|---|---|
| CS, active low | **D53 / PB0** |
| SCK | D52 / PB1 |
| MOSI | D51 / PB2 |
| MISO | D50 / PB3 |
| GND | Common ground |

Match power and logic levels to the W5500 module. RSTn needs a valid hardware
reset circuit; the driver also performs a software reset. INT is unused.
Configure CS in [board_pins.h](../src/board_pins.h); hardware SPI pins are fixed.
Keep other SPI devices deselected. The bootloader does not support SD cards.

## Program the bootloader and factory EEPROM

**This operation erases the application and may erase EEPROM.** Assign a unique
decimal serial number from 1 to 65535:

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001
```

The script:

1. Generates and validates an IDLE EEPROM record, then builds and tests.
2. Checks the ATmega2560 signature (`1E 98 01`).
3. Erases Flash and writes fuses `LF=FF`, `HF=D8`, `EF=FD` for this target.
4. Writes and verifies EEPROM and Flash in one ISP session.
5. Sets lock bits to `0F`, verifies both memories again and reads back fuses.

Any failure stops the sequence. Verification is enabled; `-F` is never used.
Unused lock bits can make the readback appear as `CF`. Boot protection is set
only after successful programming. Maintain stable power throughout installation.

Serial `0001` produces MAC `02:53:49:4F:00:01`. Factory settings are IDLE,
DHCP with fallback `192.168.1.50/24`, gateway and DNS `192.168.1.1`.
Generated device files are stored in `build/provision/`. All units share the
fallback IP; do not use it simultaneously on the same subnet. See [EEPROM](EEPROM.md).

## Script options

```powershell
# Build, generate EEPROM and print commands without accessing hardware.
.\buildAndProgram.ps1 -SerialNumber 0001 -DryRun
# Override gateway and DNS.
.\buildAndProgram.ps1 -SerialNumber 0001 -Gateway 192.168.1.254 -Dns 192.168.1.254
# Select a Python installation.
.\build.ps1 -Python 'C:\Python313\python.exe'
```

Both scripts accept `-SkipTests`; Flash bounds checks remain enabled.
The programming script also accepts `-Avrdude`, `-AvrdudeConfig`, `-Port`
(default `usb`, optionally `usb:PROGRAMMER_SERIAL`) and `-BitClock` (default 10 us).
If local execution policy blocks a trusted script, invoke it once with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

## Upload an application through CH340

Disconnect ISP, connect USB/UART and reset the board. Select **Arduino Mega or
Mega 2560 / ATmega2560** and the CH340 port in Arduino IDE, then use **Upload**.
Do not use **Burn Bootloader**: it replaces this bootloader with the standard one.
The avrdude settings are `-p m2560 -c wiring -b 115200 -D`; the maximum application
size is 253952 bytes (248 KiB).

After reset, the bootloader offers a UART window with a 2-second receive timeout.
Uploading an application does not clear PENDING. During recovery, restore the
complete application before repairing or clearing its EEPROM request.
For fault and power-loss tests, use the [validation checklist](TESTING.md).
