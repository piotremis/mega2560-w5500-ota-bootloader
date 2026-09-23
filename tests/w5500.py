"""Production W5500 driver with an independent SPI/register/ring-buffer model."""

import pathlib, subprocess, os, ctypes as C, sys

root = pathlib.Path(__file__).resolve().parents[1]
os.chdir(root)
out = root / "build/tests"
cc = (
    [str(root / "build/zig/ziglang/zig.exe"), "cc"]
    if os.name == "nt"
    else [os.environ.get("CC", "cc")]
)
variant = sys.argv[1] if len(sys.argv) > 1 else "default"
defines = []
if variant == "alternate":
    defines = ["-DW5500_CS_PORT=PORTG", "-DW5500_CS_DDR=DDRG", "-DW5500_CS_BIT=1"]
else:
    assert variant == "default"
dll = out / ("w5500-" + variant + (".dll" if os.name == "nt" else ".so"))
env = dict(
    os.environ,
    ZIG_GLOBAL_CACHE_DIR=str(out / "zig-cache"),
    ZIG_LOCAL_CACHE_DIR=str(out / "zig-local"),
)
subprocess.run(
    [
        *cc,
        "-shared",
        "-fPIC",
        "-O1",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-DHOST_W5500",
        *defines,
        "-Isrc",
        "tests/w5500_model.c",
        "src/w5500.c",
        "-o",
        str(dll),
    ],
    check=True,
    env=env,
)
lib = C.CDLL(str(dll))
u8 = C.c_uint8
u16 = C.c_uint16
p = C.c_void_p
for name, args, ret in [
    ("net_init", [p], u8),
    ("net_open", [u8, u16], u8),
    ("net_connect", [p, u16], u8),
    ("net_send", [p, u16], u8),
    ("model_rx", [u16, p, u16], None),
    ("net_recv", [p, u16], C.c_int16),
    ("udp_recv", [p, u16, p, p], C.c_int16),
]:
    f = getattr(lib, name)
    f.argtypes = args
    f.restype = ret
u8.in_dll(lib, "PORTG").value = 0x80
u8.in_dll(lib, "DDRG").value = 0x80
mac = bytes.fromhex("020102030405")
assert lib.net_init(mac)
expected = (1, 7, 130, 130) if variant == "alternate" else (1, 7, 128, 128)
assert (
    tuple(u8.in_dll(lib, n).value for n in ("PORTB", "DDRB", "PORTG", "DDRG"))
    == expected
)
common = (u8 * 64).in_dll(lib, "common")
sock = (u8 * 64).in_dll(lib, "sock")
tx = (u8 * 2048).in_dll(lib, "tx")
assert bytes(common[9:15]) == mac
assert lib.net_open(2, 68)
assert bytes(sock[4:6]) == b"\0D"
data = bytes(range(256))
outbuf = (u8 * 600)()
ip = (u8 * 4)()
port = u16()
udp = b"\xc0\xa8\x01\x01\x00\x43\x01\x00" + data
for offset in (0, 2040, 65528):
    lib.model_rx(offset, udp, len(udp))
    assert lib.udp_recv(outbuf, 600, ip, C.byref(port)) == 256
    assert (
        bytes(outbuf[:256]) == data
        and port.value == 67
        and bytes(ip) == b"\xc0\xa8\1\1"
    )
    assert lib.udp_recv(outbuf, 600, ip, C.byref(port)) == 0
lib.model_rx(0, udp, len(udp))
assert lib.udp_recv(outbuf, 10, ip, C.byref(port)) == 0
assert lib.net_connect(b"\xc0\xa8\1\2", 8080)
lib.model_rx(65528, data, len(data))
assert lib.net_recv(outbuf, 17) == 17 and bytes(outbuf[:17]) == data[:17]
sock[0x24] = 255
sock[0x25] = 248
assert lib.net_send(data, len(data))
assert bytes(tx[(65528 + i) & 2047] for i in range(256)) == data
C.c_int.in_dll(lib, "host_timeout").value = 1
assert not lib.net_send(data, len(data))
C.c_int.in_dll(lib, "host_busy").value = 1
assert not lib.net_open(2, 68)
assert C.c_int.in_dll(lib, "host_pin_errors").value == 0
msg = f"PASS ({variant} pins): CS active-low/output during every SPI byte, hardware SS output, idle GPIO states, MAC, sockets, UDP header, RX/TX wraps, timeouts.\n"
(
    out
    / ("w5500-results.txt" if variant == "default" else f"w5500-{variant}-results.txt")
).write_text(msg)
print(msg)
if variant == "default":
    subprocess.run([sys.executable, __file__, "alternate"], check=True)
