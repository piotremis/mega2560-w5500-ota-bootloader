"""Produce a metadata-only Intel HEX for EEPROM and a backend JSON manifest.
Never programs a device. An application's transactional commit is ota_request.c.
"""

import argparse, pathlib, struct, zlib, json, ipaddress, re


def valid_url(url):
    """Match the bootloader URL grammar and reject unusable IPv4 literals."""
    if not 9 <= len(url) <= 100 or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
        return False
    match = re.fullmatch(
        r"http://([A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})*)(?::([0-9]+))?/[^#]*",
        url,
    )
    if not match:
        return False
    host, port = match.groups()
    if port is not None and not 1 <= int(port) <= 65535:
        return False
    if all(c in "0123456789." for c in host):
        octets = host.split(".")
        if len(octets) != 4 or any(
            not 1 <= len(o) <= 3 or int(o) > 255 for o in octets
        ):
            return False
    return True


def ihex(address, data):
    rows = []
    for i in range(0, len(data), 16):
        b = data[i : i + 16]
        raw = bytes([len(b)]) + struct.pack(">H", address + i) + b"\0" + b
        rows.append(":" + raw.hex().upper() + f"{(-sum(raw)) & 255:02X}")
    return "\n".join(rows + [":00000001FF"]) + "\n"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("bin")
    a.add_argument("--url", required=True)
    a.add_argument("--mac", required=True)
    a.add_argument("--version", type=int, required=True)
    a.add_argument("--serial-number", type=int, default=0)
    a.add_argument("--out", default="build/request.eep")
    a.add_argument("--network", choices=("dhcp", "fallback", "static"), default="dhcp")
    a.add_argument("--ip")
    a.add_argument("--mask")
    a.add_argument("--gateway", default="0.0.0.0")
    a.add_argument("--dns", default="0.0.0.0")
    args = a.parse_args()
    if not valid_url(args.url):
        a.error("valid http://HOST[:1..65535]/PATH required, max 100 ASCII bytes")
    if not 0 <= args.version <= 0xFFFFFFFF:
        a.error("version must be 0..4294967295")
    if not 0 <= args.serial_number <= 65535:
        a.error("serial number must be 0..65535 (0 means unspecified)")
    mode = ("dhcp", "fallback", "static").index(args.network)
    addresses = bytes(16)
    if mode:
        if not args.ip or not args.mask:
            a.error("static/fallback requires --ip and --mask")
        try:
            interface = ipaddress.IPv4Interface(args.ip + "/" + args.mask)
            if (
                interface.ip.is_unspecified
                or interface.ip.is_multicast
                or interface.ip.is_loopback
            ):
                a.error("usable device IP required")
            addresses = b"".join(
                ipaddress.IPv4Address(x).packed
                for x in (args.ip, str(interface.netmask), args.gateway, args.dns)
            )
            host = args.url[7:].split("/", 1)[0].split(":", 1)[0]
            # valid_url already checked numeric literals using the bootloader's
            # decimal grammar (including leading zeroes, unlike ipaddress).
            if not all(c in "0123456789." for c in host) and args.dns == "0.0.0.0":
                a.error("hostname URL requires --dns in static/fallback mode")
        except ValueError as error:
            a.error(str(error))
    image = pathlib.Path(args.bin).read_bytes()
    url = args.url.encode("ascii")
    mac = bytes.fromhex(args.mac.replace(":", ""))
    if not 0 < len(image) <= 0x3E000:
        a.error("image must be 1..253952 bytes")
    if len(mac) != 6 or mac[0] & 1 or not any(mac):
        a.error("valid unicast MAC required")
    record = bytearray(160)
    crc = zlib.crc32(image)
    struct.pack_into(
        "<HBBIII", record, 0, 0x4F54, 1, 0xA5, len(image), crc, args.version
    )
    record[16:22] = mac
    record[22] = len(url)
    record[23 : 23 + len(url)] = url
    record[124] = mode
    record[125:141] = addresses
    struct.pack_into("<H", record, 141, args.serial_number)
    struct.pack_into("<I", record, 156, zlib.crc32(record[4:156]))
    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(ihex(3936, record))
    p.with_suffix(".json").write_text(
        json.dumps(
            {
                "format": 1,
                "network_mode": args.network,
                "version": args.version,
                "url": args.url,
                "image_size": len(image),
                "crc32": f"{crc:08x}",
                "mac": args.mac,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
