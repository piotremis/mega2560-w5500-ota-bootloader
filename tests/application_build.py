"""Link documented application API from both C and C++ against C objects."""

# SPDX-License-Identifier: GPL-2.0-or-later
import pathlib, sys, subprocess

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from build import ROOT, tool

out = ROOT / "build/tests"
out.mkdir(parents=True, exist_ok=True)
flags = [
    "-mmcu=atmega2560",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-Iapplication",
    "-Isrc",
]
objects = []
for name in (
    "application/ota_request.c",
    "application/avr_eeprom.c",
    "src/crc32.c",
    "src/eeprom_cfg.c",
):
    obj = out / ("api-" + pathlib.Path(name).stem + ".o")
    subprocess.run(
        [tool("gcc"), *flags, "-std=gnu11", "-c", name, "-o", str(obj)], check=True
    )
    objects.append(str(obj))
for language, compiler, standard in (("c", "gcc", "gnu11"), ("cpp", "g++", "gnu++11")):
    source = out / ("app_api." + language)
    # Include boot.h first to catch include-order-dependent C linkage.
    source.write_text("""#include "boot.h"
#include "ota_request.h"
#include <avr/wdt.h>
#include <avr/interrupt.h>
int main(void) {
    if (!cfg_load()) return 1;
    Config request = cfg;
    const char url[] = "http://example.com/fw.bin";
    memcpy(request.url, url, sizeof(url));
    request.url_len = sizeof(url) - 1;
    request.image_size = 9;
    request.image_crc = crc32("123456789", 9);
    request.version = 1;
    if (ota_request(&request)) {
        cli(); wdt_enable(WDTO_15MS); for (;;) {}
    }
    return 0;
}
""")
    subprocess.run(
        [
            tool(compiler),
            *flags,
            "-std=" + standard,
            str(source),
            *objects,
            "-o",
            str(out / ("app-api-" + language + ".elf")),
        ],
        check=True,
    )
(out / "application-api.txt").write_text(
    "PASS: C and C++ callers linked against C application API objects for ATmega2560. Includes cfg_load, CRC and watchdog reset. Not a deployable application.\n"
)
print("PASS: application API AVR C and C++ link")
