/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "boot.h"
/* Keep one shared CRC bit loop: inlining duplicates it across download/readback. */
uint32_t __attribute__((noinline)) crc_byte(uint32_t crc, uint8_t b) {
    crc ^= b;
    for (uint8_t i = 0; i < 8; i++) {
        uint8_t bit = crc & 1;
        crc >>= 1;
        if (bit) {
            crc ^= 0xedb88320UL;
        }
    }
    return crc;
}
uint32_t crc32(const void *data, uint16_t n) {
    const uint8_t *p = data;
    uint32_t c = 0xffffffffUL;
    while (n--) {
        c = crc_byte(c, *p++);
    }
    return ~c;
}
uint8_t range_ok(uint32_t a, uint16_t n) {
    return n && a < APP_END && n <= APP_END - a;
}
