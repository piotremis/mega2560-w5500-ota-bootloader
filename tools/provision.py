"""Generate a factory IDLE EEPROM record; never access hardware."""

# SPDX-License-Identifier: GPL-2.0-or-later
import argparse
import ipaddress
import json
import pathlib
import struct
import zlib

from eeprom import ihex


def factory_record(serial, gateway="192.168.1.1", dns="192.168.1.1"):
    """Decimal serial 1..65535 maps to the last two MAC octets, big endian."""
    if not str(serial).isascii() or not str(serial).isdecimal():
        raise ValueError("serial number must contain decimal digits only")
    number = int(serial, 10) if isinstance(serial, str) else int(serial)
    if not 1 <= number <= 65535:
        raise ValueError("serial number must be 1..65535")
    record = bytearray(160)
    struct.pack_into("<HBB", record, 0, 0x4F54, 1, 0)  # IDLE, no image or URL
    record[16:22] = bytes.fromhex("02 53 49 4f") + number.to_bytes(2, "big")
    record[124] = 1  # DHCP first, static fallback
    record[125:141] = b"".join(
        ipaddress.IPv4Address(address).packed
        for address in ("192.168.1.50", "255.255.255.0", gateway, dns)
    )
    struct.pack_into("<H", record, 141, number)
    struct.pack_into("<I", record, 156, zlib.crc32(record[4:156]))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial-number", required=True)
    parser.add_argument("--gateway", default="192.168.1.1")
    parser.add_argument("--dns", default="192.168.1.1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        record = factory_record(args.serial_number, args.gateway, args.dns)
    except ValueError as error:
        parser.error(str(error))
    serial = struct.unpack_from("<H", record, 141)[0]
    manifest = {
        "serial_number": f"{serial:04d}",
        "mac": ":".join(f"{octet:02X}" for octet in record[16:22]),
        "state": "IDLE",
        "format": 1,
        "network_mode": "dhcp_with_static_fallback",
        "ip": "192.168.1.50",
        "mask": "255.255.255.0",
        "gateway": args.gateway,
        "dns": args.dns,
        "eeprom_address": "0x0F60",
        "bytes": len(record),
    }
    target = pathlib.Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ihex(3936, record), encoding="ascii")
    target.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
