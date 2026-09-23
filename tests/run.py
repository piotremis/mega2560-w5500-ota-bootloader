"""Execute production parsers, STK dispatcher and OTA C code using host I/O mocks."""

import ctypes as C, pathlib, subprocess, sys, os, shutil, struct, zlib, unittest, random, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
out = ROOT / "build/tests"
out.mkdir(parents=True, exist_ok=True)
zig = list((ROOT / "build/tool-download").glob("ziglang*.whl"))
if os.name == "nt":
    exe = ROOT / "build/zig/ziglang/zig.exe"
    if not exe.exists():
        if not zig:
            raise SystemExit(
                "Host compiler: pip download ziglang==0.13.0 --dest build/tool-download"
            )
        with zipfile.ZipFile(zig[0]) as z:
            z.extractall(ROOT / "build/zig")
    cc = [str(exe), "cc"]
    dll = out / "host.dll"
else:
    cc = [os.environ.get("CC", "cc")]
    dll = out / "host.so"
sources = ["tests/host.c", "application/ota_request.c"] + [
    f"src/{x}.c"
    for x in (
        "crc32",
        "eeprom_cfg",
        "network_cfg",
        "dhcp",
        "dns",
        "http",
        "ota",
        "stk500",
    )
]
env = dict(
    os.environ,
    ZIG_GLOBAL_CACHE_DIR=str(out / "zig-cache"),
    ZIG_LOCAL_CACHE_DIR=str(out / "zig-local"),
)
# ELF interposition can resolve our two-argument crc32() to Python's zlib
# three-argument function. Bind definitions inside the host model to themselves.
# This flag is only for the Linux test library, never the AVR firmware.
host_link_flags = ["-Wl,-Bsymbolic"] if sys.platform.startswith("linux") else []
subprocess.run(
    [
        *cc,
        "-std=c11",
        "-O1",
        "-g",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-shared",
        "-fPIC",
        *host_link_flags,
        "-Isrc",
        *sources,
        "-o",
        str(dll),
    ],
    check=True,
    env=env,
)
if sys.platform.startswith("linux") and getattr(zlib, "__file__", None):
    # Make the regression deterministic even when Python loads zlib locally:
    # promote its symbols before loading the model. CRC/EEPROM tests must still
    # use the firmware CRC implementation, not zlib's incompatible C ABI.
    global_zlib = C.CDLL(zlib.__file__, mode=C.RTLD_GLOBAL)
lib = C.CDLL(str(dll))
U8 = C.c_uint8
U16 = C.c_uint16
U32 = C.c_uint32


def bind(n, args, ret):
    f = getattr(lib, n)
    f.argtypes = args
    f.restype = ret
    return f


ptr = C.c_void_p
bind("crc32", [ptr, U16], U32)
bind("cfg_valid", [ptr], U8)
bind("cfg_load", [], U8)
bind("range_ok", [U32, U16], U8)
bind("url_parse", [ptr, ptr], U8)
bind("http_header", [ptr, U32, ptr], C.c_int8)
bind("dns_parse", [U16, C.c_char_p, U16, ptr], U8)
bind("dns", [C.c_char_p, ptr], U8)
bind("network_configure", [], U8)
bind("dhcp_parse", [U16, U8, ptr, ptr], U8)
bind("stk_command", [U16], U16)
bind("host_stream", [ptr, U32], None)
bind("host_udp", [ptr, U16, ptr, U16], None)
bind("ota", [], U8)
bind("ota_request", [ptr], U8)
bind("cfg_bootable", [U8], U8)
packet = (U8 * 600).in_dll(lib, "packet")
flash = (U8 * 0x40000).in_dll(lib, "host_flash")
ee = (U8 * 4096).in_dll(lib, "host_eeprom")
cfg = (U8 * 160).in_dll(lib, "cfg")


class Url(C.Structure):
    _fields_ = [("host", C.c_char_p), ("path", C.c_char_p), ("port", U16)]


def load(buf, data):
    C.memmove(buf, bytes(data), len(data))


def record(
    image=b"123456789", state=0xA5, url=b"http://example.com:8080/fw.bin", mode=0
):
    b = bytearray(160)
    struct.pack_into(
        "<HBBIII", b, 0, 0x4F54, 1, state, len(image), zlib.crc32(image), 42
    )
    b[16:22] = bytes.fromhex("020102030405")
    b[22] = len(url)
    b[23 : 23 + len(url)] = url
    b[124] = mode
    if mode:
        b[125:141] = bytes(
            [10, 0, 0, 44, 255, 255, 255, 0, 10, 0, 0, 1, 192, 168, 1, 1]
        )
    struct.pack_into("<I", b, 156, zlib.crc32(b[4:156]))
    return b


def dhcp_reply(xid, mac, kind=2):
    b = bytearray(240)
    b[:3] = b"\x02\x01\x06"
    b[4:8] = xid
    b[28:34] = mac
    b[16:20] = bytes([192, 168, 1, 99])
    b[236:] = bytes.fromhex("63825363")
    b += bytes(
        [
            53,
            1,
            kind,
            54,
            4,
            192,
            168,
            1,
            1,
            1,
            4,
            255,
            255,
            255,
            0,
            3,
            4,
            192,
            168,
            1,
            1,
            6,
            4,
            192,
            168,
            1,
            1,
            255,
        ]
    )
    return b


def dns_reply(q):
    b = bytearray(q)
    b[2:4] = b"\x81\x80"
    b[6:8] = b"\x00\x01"
    b += bytes.fromhex("c00c000100010000003c0004c0a80102")
    return b


def dns_query(host=b"example.com"):
    return (
        bytes.fromhex("123401000001000000000000")
        + b"".join(bytes([len(x)]) + x for x in host.split(b"."))
        + b"\0\0\1\0\1"
    )


callback_type = C.CFUNCTYPE(U8, ptr, U16, U8)


class Tests(unittest.TestCase):
    def setUp(self):
        lib.host_reset()
        C.memset(flash, 255, len(flash))
        C.memset(ee, 255, len(ee))
        self.callbacks = []
        C.c_int.in_dll(lib, "host_ee_cut").value = -1
        C.c_int.in_dll(lib, "host_ee_writes").value = 0

    def test_crc(self):
        for data in (b"", b"123456789", bytes(range(256)), bytes(range(256)) * 200):
            self.assertEqual(lib.crc32(data, len(data)), zlib.crc32(data))

    def test_url(self):
        for text, host, path, port in [
            ("http://example.com/fw.bin", b"example.com", b"fw.bin", 80),
            ("http://x:65535/", b"x", b"", 65535),
            ("http://192.168.1.20:8080/fw.bin", b"192.168.1.20", b"fw.bin", 8080),
        ]:
            b = C.create_string_buffer(text.encode())
            u = Url()
            self.assertEqual(lib.url_parse(b, C.byref(u)), 1)
            self.assertEqual((u.host, u.path, u.port), (host, path, port))
        for text in (
            "https://x/a",
            "http:///a",
            "http://x:0/a",
            "http://x:65536/a",
            "http://x:99999999999999999999/a",
            "http://x:/a",
            "http://x/a\r\nX: y",
            "http://a..b/x",
            "http://user@x/a",
            "http://x/a#fragment",
            "http://x",
        ):
            b = C.create_string_buffer(text.encode())
            self.assertFalse(lib.url_parse(b, C.byref(Url())), text)

    def test_headers(self):
        for text in ("Content-Length: 9", "content-length:\t9 "):
            seen = U8()
            self.assertEqual(
                lib.http_header(
                    C.create_string_buffer(text.encode()), 9, C.byref(seen)
                ),
                0,
            )
            self.assertEqual(seen.value, 1)
        for text in (
            "Content-Length: 10",
            "Content-Length: 0",
            "Content-Length: -9",
            "Content-Length: 99999999999999999999",
            "Content-Length: 9junk",
            "Transfer-Encoding: chunked",
            "Content-Encoding: gzip",
            " Content-Length: 9",
            "broken",
        ):
            self.assertEqual(
                lib.http_header(
                    C.create_string_buffer(text.encode()), 9, C.byref(U8())
                ),
                -1,
                text,
            )
        self.assertEqual(
            lib.http_header(C.create_string_buffer(b""), 9, C.byref(U8())), -1
        )
        self.assertEqual(
            lib.http_header(C.create_string_buffer(b""), 9, C.byref(U8(1))), 1
        )
        self.assertEqual(
            lib.http_header(
                C.create_string_buffer(b"Content-Length: 9"), 9, C.byref(U8(1))
            ),
            -1,
        )

    def test_eeprom(self):
        b = record()
        load(cfg, b)
        self.assertTrue(lib.cfg_valid(cfg))
        for i in range(4, 160):
            bad = bytearray(b)
            bad[i] ^= 1
            load(cfg, bad)
            self.assertFalse(lib.cfg_valid(cfg), i)
        for state in (0, 0xA5):
            b[3] = state
            load(cfg, b)
            self.assertTrue(lib.cfg_valid(cfg))
        load(C.addressof(ee) + 3936, b)
        self.assertTrue(lib.cfg_load())
        lib.cfg_done()
        self.assertEqual(ee[3939], 0)

    def test_boot_policy(self):
        load(cfg, b"\xff" * 160)
        self.assertTrue(lib.cfg_bootable(0))
        for state in range(256):
            load(cfg, record(state=state))
            self.assertEqual(lib.cfg_bootable(1), state == 0)
            self.assertEqual(lib.cfg_bootable(0), state not in (0xA5, 0x5A))
        for size in (0, 0x3E001, 0xFFFFFFFF):
            b = record()
            struct.pack_into("<I", b, 4, size)
            struct.pack_into("<I", b, 156, zlib.crc32(b[4:156]))
            load(cfg, b)
            self.assertFalse(lib.cfg_valid(cfg))

    def test_uart_framing(self):
        def frame(payload, seq):
            b = (
                b"\x1b"
                + bytes([seq])
                + struct.pack(">H", len(payload))
                + b"\x0e"
                + payload
            )
            checksum = 0
            for x in b:
                checksum ^= x
            return b + bytes([checksum])

        good = frame(b"\1", 255)
        bad = bytearray(good)
        bad[-1] ^= 1
        rx = iter(bytes(bad) + b"!!!" + b"\x1b\0\xff\xff\x0e" + good + frame(b"\1", 0))
        tx = []
        gt = C.CFUNCTYPE(C.c_int16)
        pt = C.CFUNCTYPE(None, U8)
        get = gt(lambda: next(rx, -1))
        put = pt(lambda x: tx.append(x))
        lib.host_uart(get, put)
        lib.stk500()
        expected = frame(b"\1\0\10AVRISP_2", 255) + frame(b"\1\0\10AVRISP_2", 0)
        self.assertEqual(bytes(tx), expected)
        # Retain callbacks because the C library keeps these pointers.
        self.callbacks.extend([get, put])

    def test_flash_bounds(self):
        for a, n, ok in [
            (0, 256, 1),
            (0x3DF00, 256, 1),
            (0x3DFFF, 1, 1),
            (0x3DFFF, 2, 0),
            (0x3E000, 256, 0),
            (0xFFFFFFFF, 2, 0),
            (0, 0, 0),
        ]:
            self.assertEqual(lib.range_ok(a, n), ok)

    def test_request_commit(self):
        rec = record()
        load(cfg, rec)
        self.assertTrue(lib.ota_request(cfg))
        self.assertEqual(bytes(ee[3936:]), rec)
        self.assertFalse(lib.ota_request(cfg))

    def test_request_url_validation(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from eeprom import valid_url

        cases = {
            "http://example.com/fw.bin": True,
            "http://x/": True,
            "http://x:1/": True,
            "http://x:65535/a?b=c": True,
            "http://010.002.003.004/fw": True,
            "http://123.example.com/fw": True,
            "http://x:00080/fw": True,
            "http://example.com:0/fw.bin": False,
            "http://x:65536/fw": False,
            "http://x:/fw": False,
            "http://example.com": False,
            "http://x/fw#fragment": False,
            "http://x/a b": False,
            "http://x/\r\nHost:evil": False,
            "https://x/fw": False,
            "http://user@x/fw": False,
            "http://x../fw": False,
            "http://" + "a" * 64 + "/fw": False,
            "http://256.1.2.3/fw": False,
            "http://1.2.3/fw": False,
            "http://0000.1.2.3/fw": False,
            "http://x/a\0hidden": False,
        }
        rng = random.Random(68)
        for _ in range(300):
            host = rng.choice(("example.com", "1.2.3.4", "1.2.3", "x..y"))
            port = rng.choice(("", ":0", ":65535", ":65536", ":080"))
            tail = rng.choice(("/fw", "/", "", "/a#b", "/a?b=c"))
            url = "http://" + host + port + tail
            cases[url] = valid_url(url)
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(valid_url(url), expected)
                C.memset(ee, 255, len(ee))
                C.c_int.in_dll(lib, "host_ee_writes").value = 0
                data = record(url=url.encode())
                load(cfg, data)
                self.assertEqual(bool(lib.ota_request(cfg)), expected)
                if not expected:
                    self.assertEqual(bytes(ee), b"\xff" * len(ee))
                    self.assertEqual(C.c_int.in_dll(lib, "host_ee_writes").value, 0)
                else:
                    self.assertEqual(bytes(ee[3936:]), bytes(cfg))
                    mutable = C.create_string_buffer(url.encode())
                    parsed = Url()
                    self.assertTrue(lib.url_parse(mutable, C.byref(parsed)))
                    self.assertEqual(bytes(cfg[23 : 23 + len(url)]), url.encode())

    def test_generator_rejects_bad_url(self):
        firmware = out / "url-validation.bin"
        firmware.write_bytes(b"123456789")
        target = out / "url-validation.eep"
        sentinel = b"existing record must not be overwritten"
        target.write_bytes(sentinel)
        result = subprocess.run(
            [
                sys.executable,
                "tools/eeprom.py",
                str(firmware),
                "--url",
                "http://example.com:0/fw.bin",
                "--mac",
                "02:01:02:03:04:05",
                "--version",
                "1",
                "--out",
                str(target),
            ],
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), sentinel)

    def test_missing_record_does_not_write(self):
        for initial in (b"\xff" * 160, bytes(160), bytes([0x33]) * 160):
            load(C.addressof(ee) + 3936, initial)
            valid = lib.cfg_load()
            self.assertFalse(valid)
            self.assertTrue(lib.cfg_bootable(valid))
            self.assertEqual(bytes(ee[3936:]), initial)
            self.assertEqual(C.c_int.in_dll(lib, "host_ee_writes").value, 0)

    def test_load_preserves_updates(self):
        for state in (0, 0xA5, 0x5A):
            for broken in (False, True):
                rec = record(state=state)
                if broken:
                    rec[156] ^= 1
                load(C.addressof(ee) + 3936, rec)
                valid = lib.cfg_load()
                self.assertEqual(valid, not broken)
                self.assertEqual(lib.cfg_bootable(valid), state == 0)
                self.assertEqual(bytes(ee[3936:]), rec)
                self.assertEqual(C.c_int.in_dll(lib, "host_ee_writes").value, 0)

    def test_factory_provisioning(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from provision import factory_record

        for serial in ("0001", "0002", "0256", "65535"):
            C.c_int.in_dll(lib, "host_ee_writes").value = 0
            rec = factory_record(serial)
            number = int(serial)
            self.assertEqual(
                rec[16:22], bytes.fromhex("0253494f") + number.to_bytes(2, "big")
            )
            self.assertEqual(struct.unpack_from("<H", rec, 141)[0], number)
            self.assertEqual(
                rec[124:137],
                bytes([1, 192, 168, 1, 50, 255, 255, 255, 0, 192, 168, 1, 1]),
            )
            load(C.addressof(ee) + 3936, rec)
            self.assertTrue(lib.cfg_load())
            self.assertTrue(lib.cfg_bootable(1))
            self.assertEqual(C.c_int.in_dll(lib, "host_ee_writes").value, 0)
            cfg[3] = 0xA5
            self.assertFalse(lib.cfg_valid(cfg))  # No image/URL: cannot start OTA.
            # Application loads factory fields, then adds image metadata.
            requested = record()
            requested[16:22] = rec[16:22]
            requested[124:156] = rec[124:156]
            load(cfg, requested)
            self.assertTrue(lib.ota_request(cfg))
            self.assertEqual(bytes(ee[3952:3958]), bytes(rec[16:22]))
            self.assertEqual(bytes(ee[4077:4079]), bytes(rec[141:143]))
        for serial in ("0", "65536", "-1", "1.0", "abc", "", "0x10"):
            with self.assertRaises(ValueError):
                factory_record(serial)

    def test_eeprom_power_cut_every_write(self):
        for initial in (b"\xff" * 160, record(state=0)):
            for cut in range(170):
                load(C.addressof(ee) + 3936, initial)
                load(cfg, record(b"new image", mode=2))
                C.c_int.in_dll(lib, "host_ee_cut").value = cut
                C.c_int.in_dll(lib, "host_ee_writes").value = 0
                lib.ota_request(cfg)
                valid = lib.cfg_load()
                if ee[3939] == 0xA5:
                    self.assertTrue(valid)
                    self.assertEqual(bytes(ee[3936:]), record(b"new image", mode=2))

    def test_dns(self):
        q = dns_query()
        b = dns_reply(q)
        load(packet, b)
        ip = (U8 * 4)()
        self.assertTrue(lib.dns_parse(len(b), b"example.com", 0x1234, ip))
        self.assertEqual(bytes(ip), bytes([192, 168, 1, 2]))
        for cut in range(len(b)):
            load(packet, b)
            self.assertFalse(lib.dns_parse(cut, b"example.com", 0x1234, ip))
        for offset, value in [
            (0, 0),
            (2, 0x83),
            (3, 0x83),
            (len(q), 0xFF),
            (len(q) + 1, len(q)),
            (len(q) + 3, 28),
        ]:
            bad = bytearray(b)
            bad[offset] = value
            load(packet, bad)
            self.assertFalse(lib.dns_parse(len(bad), b"example.com", 0x1234, ip))
        load(packet, b)
        self.assertFalse(lib.dns_parse(len(b), b"other.com", 0x1234, ip))

    def test_dhcp(self):
        xid = b"ABCD"
        mac = bytes.fromhex("020102030405")
        offer = dhcp_reply(xid, mac)
        load(packet, offer)
        self.assertTrue(lib.dhcp_parse(len(offer), 2, xid, mac))
        ack = dhcp_reply(xid, mac, 5)
        load(packet, ack)
        self.assertTrue(lib.dhcp_parse(len(ack), 5, xid, mac))
        for cut in range(len(ack)):
            load(packet, ack)
            self.assertFalse(lib.dhcp_parse(cut, 5, xid, mac))
        for offset in (4, 28, 236, 16, 247):
            b = bytearray(ack)
            b[offset] ^= 1
            load(packet, b)
            self.assertFalse(lib.dhcp_parse(len(b), 5, xid, mac))

    def command(self, b):
        load(packet, b)
        return bytes(packet[: lib.stk_command(len(b))])

    def address(self, a):
        self.assertEqual(self.command(b"\6" + struct.pack(">I", a)), b"\6\0")

    def test_stk(self):
        self.assertEqual(self.command(b"\1"), b"\1\0\10AVRISP_2")
        self.assertEqual(
            self.command(bytes([0x1D, 4, 4, 0, 0x30, 0, 1, 0])),
            bytes([0x1D, 0, 0, 0x30, 0, 0x98, 0]),
        )
        for a in (0, 0x10000, 0x1DF80):
            self.address(a | 0x80000000)
            data = bytes(range(256))
            self.assertEqual(self.command(b"\x13\1\0" + bytes(7) + data), b"\x13\0")
            self.address(a)
            self.assertEqual(self.command(b"\x14\1\0\x20"), b"\x14\0" + data + b"\0")
        self.address(0x1F000)
        self.assertEqual(self.command(b"\x13\1\0" + bytes(263)), b"\x13\xc0")
        self.assertEqual(bytes(flash[0x3E000:]), bytes([255]) * 8192)
        self.address(0x1F000)
        self.assertEqual(
            self.command(b"\x14\1\0\x20"), b"\x14\0" + b"\xff" * 256 + b"\0"
        )
        self.address(123)
        self.assertEqual(self.command(b"\x15\0\3" + bytes(7) + b"abc"), b"\x15\0")
        self.address(123)
        self.assertEqual(self.command(b"\x16\0\3\0"), b"\x16\0abc\0")
        for b in (b"\x06", b"\x13\0\0" + bytes(7), b"\x13\0\3" + bytes(7) + b"abc"):
            self.assertEqual(self.command(b)[1], 0xC0)

    def network(self, image, header=None, drop=None):
        requests = []

        def sent(p, n, kind):
            q = C.string_at(p, n)
            requests.append((kind, q))
            if kind == 2 and drop != "dhcp":
                reply = dhcp_reply(q[4:8], q[28:34], 2 if q[242] == 1 else 5)
                lib.host_udp(bytes(reply), len(reply), bytes([192, 168, 1, 1]), 67)
            if kind == 3 and drop != "dns":
                reply = dns_reply(q)
                lib.host_udp(bytes(reply), len(reply), bytes([192, 168, 1, 1]), 53)
            if kind == 1:
                h = (
                    header
                    if header is not None
                    else b"HTTP/1.0 200 OK\r\nContent-Length: "
                    + str(len(image)).encode()
                    + b"\r\n\r\n"
                )
                data = h + image
                lib.host_stream(data, len(data))
            return 1

        cb = callback_type(sent)
        self.callbacks.append(cb)
        lib.host_callback(cb)
        return requests

    def test_static_and_fallback(self):
        image = b"static firmware"
        for mode, drop, expects_dhcp, expects_static in (
            (2, "dhcp", False, True),
            (1, "dhcp", True, True),
            (1, None, True, False),
        ):
            lib.host_reset()
            rec = record(image, mode=mode)
            load(cfg, rec)
            self.assertTrue(lib.cfg_valid(cfg))
            requests = self.network(image, drop=drop)
            self.assertTrue(lib.ota())
            self.assertEqual(any(k == 2 for k, _ in requests), expects_dhcp)
            self.assertTrue(any(k == 3 for k, _ in requests))
            actual = bytes((U8 * 12).in_dll(lib, "host_network"))
            if expects_static:
                self.assertEqual(actual, bytes(rec[125:137]))
            else:
                self.assertEqual(actual[:4], bytes([192, 168, 1, 99]))
            self.assertEqual(bytes(flash[: len(image)]), image)

    def test_static_ip_no_dhcp_no_dns(self):
        image = b"offline network"
        load(cfg, record(image, mode=2, url=b"http://10.0.0.1/fw.bin"))
        requests = self.network(image, drop="dns")
        self.assertTrue(lib.ota())
        self.assertEqual([k for k, _ in requests], [1])

    def test_network_record_integrity(self):
        good = record(mode=2)
        for index in range(124, 160):
            bad = bytearray(good)
            bad[index] ^= 1
            load(cfg, bad)
            self.assertFalse(lib.cfg_valid(cfg), index)
        load(cfg, record(mode=3))
        self.assertFalse(lib.cfg_valid(cfg))
        old = bytearray(good)
        old[2] = 99
        load(cfg, old)
        self.assertFalse(lib.cfg_valid(cfg))

    def test_ipv4_literal(self):
        requests = self.network(b"", drop="dns")
        ip = (U8 * 4)()
        for host, expected in [
            (b"192.168.1.20", bytes([192, 168, 1, 20])),
            (b"0.0.0.0", bytes(4)),
            (b"255.255.255.255", bytes([255]) * 4),
            (b"010.002.003.004", bytes([10, 2, 3, 4])),
        ]:
            self.assertTrue(lib.dns(host, ip), host)
            self.assertEqual(bytes(ip), expected)
        for host in (
            b"",
            b"1",
            b"1.2.3",
            b"1.2.3.4.5",
            b"1..2.3",
            b"256.1.2.3",
            b"999999999999.1.2.3",
            b"1.2.3.",
            b".1.2.3",
            b"0000.1.2.3",
        ):
            self.assertFalse(lib.dns(host, ip), host)
        self.assertEqual(requests, [])

    def test_ota_ipv4_without_dns(self):
        image = bytes(range(256)) + b"last page"
        for suffix, port in ((b"", 80), (b":8080", 8080)):
            load(cfg, record(image, url=b"http://192.168.1.20" + suffix + b"/fw.bin"))
            requests = self.network(image, drop="dns")
            self.assertTrue(lib.ota())
            self.assertEqual(bytes(flash[: len(image)]), image)
            self.assertFalse(any(kind == 3 for kind, _ in requests))
            self.assertTrue(any(kind == 2 for kind, _ in requests))
            http = next(q for kind, q in requests if kind == 1)
            self.assertIn(b"Host: 192.168.1.20" + suffix + b"\r\n", http)
            self.assertEqual(
                bytes((U8 * 4).in_dll(lib, "host_connect_ip")), bytes([192, 168, 1, 20])
            )
            self.assertEqual(U16.in_dll(lib, "host_connect_port").value, port)

    def test_numeric_prefix_hostname_uses_dns(self):
        load(cfg, record(url=b"http://123.example.com/fw.bin"))
        requests = self.network(b"123456789")
        self.assertTrue(lib.ota())
        self.assertTrue(any(kind == 3 for kind, _ in requests))

    def test_ota_full_stream(self):
        for n in (1, 255, 256, 257, 700, 0x3E000):
            image = bytes((i * 7) & 255 for i in range(n))
            load(cfg, record(image))
            self.network(image)
            C.c_int.in_dll(lib, "host_chunk").value = 17
            self.assertEqual(lib.ota(), 1, n)
            self.assertEqual(bytes(flash[:n]), image)
            self.assertEqual(bytes(flash[0x3E000:]), b"\xff" * 8192)

    def test_ota_failure_and_restart(self):
        image = bytes(range(256)) * 4
        rec = record(image)
        load(C.addressof(ee) + 3936, rec)
        lib.cfg_load()
        self.network(image)
        C.c_int.in_dll(lib, "host_cut").value = 2
        self.assertFalse(lib.ota())
        self.assertEqual(ee[3939], 0xA5)
        lib.host_reset()
        lib.cfg_load()
        self.network(image)
        self.assertTrue(lib.ota())
        self.assertEqual(ee[3939], 0xA5)
        lib.cfg_done()
        self.assertEqual(ee[3939], 0)
        bad = bytearray(rec)
        bad[8] ^= 1
        load(cfg, bad)
        self.network(image)
        self.assertFalse(lib.ota())
        load(cfg, rec)
        self.network(image)
        C.c_int.in_dll(lib, "host_corrupt").value = 1
        self.assertFalse(lib.ota())

    def test_ota_http_errors(self):
        image = b"123456789"
        for header in (
            b"HTTP/1.0 404 Nope\r\nContent-Length: 9\r\n\r\n",
            b"HTTP/1.0 200 OK\r\n\r\n",
            b"HTTP/1.0 200 OK\r\nContent-Length: 10\r\n\r\n",
            b"HTTP/1.0 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"HTTP/1.0 200 OK\r\nContent-Length: 9\r\nContent-Length: 9\r\n\r\n",
            b"HTTP/1.0 200 OK\r\nContent-Length: 9\n\n",
        ):
            load(cfg, record(image))
            self.network(image, header)
            self.assertFalse(lib.ota())
            self.assertEqual(C.c_int.in_dll(lib, "host_writes").value, 0)
        load(cfg, record(image))
        self.network(image[:-1], b"HTTP/1.0 200 OK\r\nContent-Length: 9\r\n\r\n")
        self.assertFalse(lib.ota())
        for drop in ("dhcp", "dns"):
            load(cfg, record(image))
            requests = self.network(image, drop=drop)
            self.assertFalse(lib.ota())
            self.assertGreaterEqual(len(requests), 3)

    def test_parser_fuzz(self):
        rng = random.Random(2560)
        ip = (U8 * 4)()
        for _ in range(2000):
            n = rng.randrange(600)
            load(packet, rng.randbytes(n))
            lib.dns_parse(n, b"example.com", 0x1234, ip)
            lib.dhcp_parse(n, 5, b"ABCD", b"ABCDEF")


if __name__ == "__main__":
    with (out / "results.txt").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        )
    print((out / "results.txt").read_text())
    sys.exit(not result.wasSuccessful())
