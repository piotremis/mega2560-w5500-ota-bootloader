# EEPROM format and application API

[Documentation](README.md) / EEPROM

## Record layout

Format **1** reserves exactly 160 bytes at `0x0F60–0x0FFF` (3936–4095).
The first 3936 bytes remain available to the application. UART EEPROM operations
can access all 4096 bytes, including this record; applications must honor the reservation.

| Offset | Bytes | Field and meaning |
|---:|---:|---|
| 0 | 2 | `magic`: 0x4F54, stored as 54 4F |
| 2 | 1 | `format`: 1 |
| 3 | 1 | `state`: 00 IDLE, A5 PENDING, 5A ARMING |
| 4 | 4 | `image_size`: 1–253952 for OTA; 0 for factory IDLE |
| 8 | 4 | `image_crc`: expected firmware CRC32 |
| 12 | 4 | `version`: requested firmware version; no downgrade policy |
| 16 | 6 | `mac`: nonzero unicast MAC |
| 22 | 1 | `url_len`: 9–100 for OTA; 0 for factory IDLE |
| 23 | 101 | `url`: ASCII text and terminating NUL; zero unused bytes |
| 124 | 1 | `network_mode`: 0 DHCP, 1 DHCP/fallback, 2 static |
| 125 | 4 | `ip`: device IPv4 address, network-order octets |
| 129 | 4 | `mask`: subnet mask |
| 133 | 4 | `gateway`: 0.0.0.0 allowed for a server on the local subnet |
| 137 | 4 | `dns`: 0.0.0.0 allowed with a literal IPv4 URL |
| 141 | 2 | `serial_number`: 1–65535 during factory provisioning |
| 143 | 13 | Reserved; write zeroes |
| 156 | 4 | `record_crc`: CRC32 of bytes 4–155 inclusive |

Multibyte integers are little-endian. IPv4 addresses and MAC are byte arrays.
The C structure is packed and its size is asserted for both C and C++.
CRC32 uses the reflected IEEE polynomial `0xEDB88320`, initial value and final
XOR `0xFFFFFFFF`. The test vector `123456789` gives `CBF43926`.
Magic, format and state are checked separately. State is excluded from CRC so
clearing PENDING does not invalidate the record.

The record remains format 1. Earlier 128-byte development layouts are not read
or migrated. Reprovision when moving from those layouts; use matching application
helpers and generators. Release version and EEPROM format are separate identifiers.

## Startup policy

The bootloader reads EEPROM but does not create or repair missing records.

| Condition | Behavior |
|---|---|
| Valid IDLE | Start the existing application after the UART window |
| Valid PENDING | Attempt OTA; start only after verification |
| Raw state PENDING or ARMING, even with invalid metadata | Block application startup; retain UART recovery |
| Valid record with an unknown state | Block application startup |
| Missing/invalid record with another raw state | Disable OTA; permit existing application startup |

Factory IDLE contains identity and network settings with zero URL, size, image
CRC and version. Changing only its state to PENDING is insufficient: image
metadata is required. IDLE after a successful update may retain the last request.
A normal reset does not write EEPROM. The single-record design cannot recognize
every combination of corruption: changing both the state and metadata can conceal
an interrupted update. Ordinary power loss during download does not rewrite the record.

## Request an update from the application

Load the provisioned record with `cfg_load()`, copy `cfg`, preserve identity and
network settings, and set URL, URL length, image size, CRC and version.
`ota_request()` fills magic/format/record CRC, validates the record and URL, and
refuses to replace PENDING/ARMING. URL parsing is shared with the bootloader; the
API also checks numeric IPv4 and exact URL length before any EEPROM write.

The durable write order is:

1. Write ARMING to prevent startup after interrupted preparation.
2. Invalidate both magic bytes.
3. Write payload bytes 4–155, then CRC bytes 156–159.
4. Write format and both magic bytes.
5. Write PENDING last and wait for EEPROM completion.
6. The application enables the watchdog and waits for reset.

Example inside an application function, after receiving update metadata:

```c
#include "ota_request.h"
#include <avr/interrupt.h>
#include <avr/wdt.h>

Config request;
if (!cfg_load()) { return; } /* Provisioning must be valid. */
request = cfg;               /* Preserve MAC, serial and network settings. */
/* Set request.url, url_len, image_size, image_crc and version here. */
if (ota_request(&request)) {
    cli();
    wdt_enable(WDTO_15MS);
    for (;;) {}
}
```

Compile and link these files as C, including when called from an Arduino C++ sketch:

- `application/ota_request.c`
- `application/avr_eeprom.c`
- `src/crc32.c`
- `src/eeprom_cfg.c`

Keep the shared headers available. Do not link bootloader `main.c` or `platform.c`
into the application. Public declarations use C linkage for C++ callers.
The application/backend owns the update UI and version decision.

Interrupted preparation before the final commit requires record repair through
UART/ISP. Once PENDING is accepted, bootloader metadata remains unchanged until
both image CRC checks pass. Success changes only state to IDLE. Power loss before
that write retries OTA; interruption during it can leave PENDING, IDLE or an
unknown state. The image has already passed verification, but unknown states are
not repaired automatically. No A/B storage or rollback is provided.

## Network configuration

| Mode | Constant | Behavior |
|---:|---|---|
| 0 | `NETWORK_DHCP` | DHCP only; failure aborts the OTA attempt |
| 1 | `NETWORK_FALLBACK` | Try DHCP, then use stored static settings on failure |
| 2 | `NETWORK_STATIC` | Use stored settings immediately; do not send DHCP |

Network fields share the record CRC and commit. Preserve them in each request;
zero-initializing a record selects DHCP. Choose a unique device IP and suitable
mask/gateway. The bootloader checks CRC and mode, not IP conflicts or network
administration errors. Hostname URLs need a reachable DNS server; IPv4 URLs do not.
Fallback waits until DHCP attempts finish. Example in C:

```c
request.network_mode = NETWORK_STATIC;
memcpy(request.ip,      (uint8_t[]){192,168,1,50}, 4);
memcpy(request.mask,    (uint8_t[]){255,255,255,0}, 4);
memcpy(request.gateway, (uint8_t[]){192,168,1,1}, 4);
memcpy(request.dns,     (uint8_t[]){192,168,1,1}, 4);
```

## Factory provisioning

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001
.\buildAndProgram.ps1 -SerialNumber 0002
.\buildAndProgram.ps1 -SerialNumber 0001 -DryRun
```

Serial numbers are decimal 1–65535, displayed with at least four digits. The MAC
is locally administered/unicast: prefix `02:53:49:4F`, followed by the serial in
big-endian byte order. The record's integer serial field is little-endian.

| Serial | MAC |
|---|---|
| 0001 | 02:53:49:4F:00:01 |
| 0002 | 02:53:49:4F:00:02 |
| 0256 | 02:53:49:4F:01:00 |

The factory record is IDLE, mode 1, fallback `192.168.1.50/24`, gateway/DNS
`192.168.1.1`. Override gateway/DNS with `-Gateway` and `-Dns`.
The script validates inputs before opening the programmer, writes EEPROM and
Flash before lock bits, and verifies both. Files are `build/provision/0001.eep`
and `.json`; do not publish device-specific records.

Serials must be unique. They do not change the fallback IP: multiple devices
cannot use the default .50 simultaneously on one subnet. To generate without programming:

```sh
python tools/provision.py --serial-number 0001 --out build/provision/0001.eep
```

## Backend and ISP metadata generator

```sh
avr-objcopy -O binary -R .eeprom application.elf firmware.bin
python tools/eeprom.py firmware.bin --url http://example.com:8080/firmware.bin --mac 02:01:02:03:04:05 --version 42 --out build/request.eep
python tools/eeprom.py firmware.bin --url http://192.168.1.10/fw.bin --mac 02:01:02:03:04:05 --version 42 --network static --ip 192.168.1.50 --mask 255.255.255.0 --gateway 192.168.1.1 --out build/request.eep
```

These MAC values are examples; use the device's provisioned identity. Specify
`--serial-number` to preserve its serial (default 0 means unspecified).
Use `--network fallback` for DHCP first, and `--dns` for hostname URLs with
static/fallback settings. The tool creates a complete PENDING record as EEPROM
Intel HEX plus a JSON manifest; it does not create the OTA firmware or program hardware.
Factory IDLE is generated only by `tools/provision.py`.

The BIN must begin at application address 0 and contain no bootloader. Exclude
`.eeprom` during conversion; an ELF without data at address 0 is not a valid boot image.
Install generated EEPROM with stable power and the MCU held in reset through ISP.
Writing a prebuilt EEPROM file does not guarantee transactional order; a running
application must use `ota_request()`. Restore the complete application before
clearing a damaged request. Configuration CRC detects accidental corruption,
not deliberate modification. Replacing an existing PENDING request is forbidden.
