/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "net.h"
uint8_t ota(void) {
    Url u;
    uint8_t ip[4];
    if (!url_parse(cfg.url, &u) || !net_init(cfg.mac) || !network_configure() || !dns(u.host, ip) ||
        !http_open(&u, ip, cfg.image_size)) {
        return 0;
    }
#if STAGE >= 9
    /* The shared page buffer is padded, then committed one complete SPM page at a time. */
    uint32_t at = 0, crc = 0xffffffffUL;
    while (at < cfg.image_size) {
        memset(page, 255, sizeof(page));
        uint16_t n = cfg.image_size - at > 256 ? 256 : cfg.image_size - at;
        for (uint16_t i = 0; i < n; i++) {
            int16_t c = http_byte();
            if (c < 0) {
                return 0;
            }
            page[i] = c;
#if STAGE >= 10
            crc = crc_byte(crc, c);
#endif
        }
        if (!flash_write(at, page)) {
            return 0;
        }
        at += n;
    }
#if STAGE >= 10
    if (~crc != cfg.image_crc) {
        return 0;
    }
    /* Verify actual Flash, including the final partial page only up to image_size. */
    crc = 0xffffffffUL;
    for (at = 0; at < cfg.image_size; at++) {
        crc = crc_byte(crc, flash_read(at));
    }
    if (~crc != cfg.image_crc) {
        return 0;
    }
#else
    (void)crc;
#endif
    net_close();
    return 1;
#else
    return 0; /* Intermediate stage never marks an unprogrammed image complete. */
#endif
}
