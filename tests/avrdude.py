"""Real avrdude -c wiring against production stk500() C via TCP UART substitute.
Run tests/run.py first. This tests protocol, not AVR execution or physical UART.
"""

import ctypes as C, pathlib, socket, threading, subprocess, json, os, functools

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
dll = ROOT / ("build/tests/host.dll" if os.name == "nt" else "build/tests/host.so")
lib = C.CDLL(str(dll))
flash = (C.c_uint8 * 0x40000).in_dll(lib, "host_flash")
ee = (C.c_uint8 * 4096).in_dll(lib, "host_eeprom")
C.memset(flash, 255, len(flash))
C.memset(ee, 255, len(ee))
avrdir = pathlib.Path.home() / "AppData/Local/Arduino15/packages/arduino/tools/avrdude"
exe = sorted(avrdir.glob("*/bin/avrdude.exe"))[-1]
conf = next(exe.parent.parent.rglob("avrdude.conf"))
out = ROOT / "build/tests"
image = bytes((i * 37 + 3) & 255 for i in range(0x3E000))
(out / "application.bin").write_bytes(image)
eeprom = bytes(range(256)) * 16
(out / "eeprom.bin").write_bytes(eeprom)
server = socket.socket()
server.bind(("127.0.0.1", 0))
server.listen()
port = server.getsockname()[1]
get_type = C.CFUNCTYPE(C.c_int16)
put_type = C.CFUNCTYPE(None, C.c_uint8)
trace = []
failures = []


def serve():
    conn, _ = server.accept()
    conn.settimeout(5)
    rx = bytearray()
    tx = bytearray()

    @get_type
    def get():
        try:
            b = conn.recv(1)
            if not b:
                return -1
            rx.extend(b)
            if len(rx) >= 5 and len(rx) == int.from_bytes(rx[2:4], "big") + 6:
                trace.append(
                    {
                        "command": hex(rx[5]),
                        "length": int.from_bytes(rx[2:4], "big"),
                        "seq": rx[1],
                    }
                )
                rx.clear()
            return b[0]
        except OSError:
            return -1

    @put_type
    def put(b):
        tx.append(b)
        if len(tx) >= 5 and len(tx) == int.from_bytes(tx[2:4], "big") + 6:
            try:
                conn.sendall(tx)
            except OSError as e:
                failures.append(str(e))
            tx.clear()

    lib.host_uart(get, put)
    try:
        lib.stk500()
    finally:
        conn.close()


t = threading.Thread(target=serve)
t.start()
args = [
    str(exe),
    "-C",
    str(conf),
    "-p",
    "m2560",
    "-c",
    "wiring",
    "-P",
    f"net:127.0.0.1:{port}",
    "-b",
    "115200",
    "-D",
    "-v",
    "-U",
    f"flash:w:{out / 'application.bin'}:r",
    "-U",
    f"eeprom:w:{out / 'eeprom.bin'}:r",
]
proc = subprocess.run(
    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90
)
t.join(6)
server.close()
(out / "avrdude.txt").write_text(proc.stdout.decode(errors="replace"))
(out / "avrdude-trace.json").write_text(json.dumps(trace, indent=2))
print(proc.stdout.decode(errors="replace")[-3500:])
assert proc.returncode == 0, (proc.returncode, failures)
assert bytes(flash[: len(image)]) == image
assert bytes(flash[0x3E000:]) == b"\xff" * 8192
assert bytes(ee) == eeprom
print(
    "PASS: real avrdude wiring upload+verify, 248 KiB Flash and 4 KiB EEPROM; boot area unchanged."
)
