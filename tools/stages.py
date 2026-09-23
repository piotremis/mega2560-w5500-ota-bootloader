from build import build

for stage in (
    "serial",
    "w5500",
    "dhcp",
    "dns",
    "http",
    "eeprom",
    "stream",
    "crc",
    "recovery",
    "final",
):
    build(stage)
