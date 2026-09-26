# OTA protocol

[Documentation](README.md) / OTA

## Update sequence

The application requests an update by committing EEPROM metadata and resetting.
The bootloader does not discover updates, compare versions or expose an endpoint.

```text
UART recovery window -> valid PENDING record -> W5500 initialization
-> DHCP or static configuration -> IPv4 literal or DNS A lookup
-> HTTP GET -> Flash pages -> download CRC -> Flash readback CRC
-> IDLE -> application
```

## Network behavior

Socket 0 is reused sequentially for DHCP, DNS and HTTP. Its 2 KiB RX and TX
buffers reside in the W5500, not AVR SRAM. Other sockets remain closed.
TCP/IP runs in the controller; the DNS server address is a four-byte AVR variable.

| Service | Behavior | Limits |
|---|---|---|
| DHCP | UDP 68 to broadcast port 67; DISCOVER/OFFER and REQUEST/ACK | Three attempts per phase; 2-second response windows |
| DNS | UDP port 53; one server; A/IN query | Three attempts; 2-second response windows |
| HTTP | Outbound TCP; HTTP/1.0 GET | 3-second connect, send and receive-inactivity timeouts |

DHCP validates BOOTP fields, transaction ID, MAC, cookie, option lengths and
server identifier. ACK must match the offer and include subnet mask, router and
DNS. Missing required options fail the attempt. NAK is rejected; the next full
OTA attempt starts with DISCOVER. Lease renewal/rebinding, option overload,
lease persistence and ARP conflict detection are not implemented.

DNS verifies source IP/port, ID, flags, question, answer owner and lengths.
Name compression is supported with a bounded pointer traversal; cycles and
truncated messages are rejected. No CNAME chain, AAAA, DNSSEC, EDNS or TCP fallback
is supported. Replies must fit the 600-byte packet buffer (classic DNS is 512 bytes).

Network modes are DHCP only, DHCP with static fallback, or forced static.
The complete configuration lives in the [EEPROM record](EEPROM.md).
Even for an IPv4 URL, DHCP mode requires the DNS option in ACK; reaching that
DNS server is unnecessary when the URL contains an IP address.

## URL contract

Use `http://HOST[:PORT]/PATH`, up to 100 ASCII bytes. Port defaults to 80 and must
be in 1–65535. Spaces, control characters, non-ASCII bytes, fragments (`#`),
userinfo and IPv6 are unsupported. Host labels are limited to 63 characters.
Root `/` and query strings are supported. Supply any required percent-encoding
in the backend; the bootloader does not perform it.

An IPv4 literal requires four decimal octets, each 1–3 digits and 0–255. Leading
zeroes are decimal, not octal. Numeric-only hosts are parsed as IPv4 and never
sent to DNS, even when malformed. `123.example.com` still uses DNS.

The application API and metadata generator reject invalid URLs before committing
PENDING. A valid IPv4 URL skips the DNS socket entirely.

## HTTP response contract

```http
GET /firmware/mega.bin HTTP/1.0
Host: example.com:8080
Connection: close

```

Lines use CRLF on the wire. The response must meet all these requirements:

- HTTP/1.0 or HTTP/1.1 status **200**.
- Exactly one **Content-Length**, equal to EEPROM `image_size`, from 1 to 253952.
- CRLFCRLF header termination; at most 2048 header bytes and 255 bytes per line.
- No Transfer-Encoding or Content-Encoding header; either is rejected.

Header names are case-insensitive. Unknown ordinary headers are ignored.
TLS, redirects, chunking, compression, authentication, cookies, multipart, POST
and JSON are not implemented. There is no absolute transfer deadline: a server
that keeps sending data can extend an attempt. Reset/DTR reopens UART recovery.

## Programming and recovery

The body streams through a 600-byte buffer into a 256-byte Flash page buffer.
Each page is erased and written with interrupts disabled. The final partial page
is padded with `0xFF`. Pages beyond the image remain unchanged and are excluded
from CRC. Every SPM write is aligned and bounded by `address + 256 <= 0x3E000`.
These checks also protect UART writes; lock bits provide additional protection.

CRC32 covers exactly `image_size` received bytes, followed by a second CRC over
the same range read from Flash. Only two successful comparisons allow IDLE.
HTTP errors, timeouts, size mismatch, CRC mismatch or programming failure leave
PENDING set and prevent application startup. D13 lights, a new UART window opens,
and a complete OTA attempt follows. Restart always downloads from byte zero;
HTTP Range and partial resume are unsupported.

Bytes after Content-Length are not part of the image. The connection closes once
the image is consumed. Serve an immutable raw BIN with no vendor header or Intel
HEX encoding, and avoid compression, redirects or HTTPS-only hosting.

**CRC32 checks integrity, not authenticity.** An active attacker can alter HTTP
traffic and metadata. This version implements neither signatures nor TLS.
Recovery is not rollback: programming destroys the previous application. If the
server remains unavailable, recover through UART/ISP. Interrupted request creation
and corrupted EEPROM have additional rules described in [EEPROM](EEPROM.md).
