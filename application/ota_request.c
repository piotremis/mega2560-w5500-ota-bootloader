/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ota_request.h"
#include "../src/url_parse.h"
uint8_t ota_request(Config *c) {
    uint8_t state = ee_read(CFG_BASE + 3);
    if (state != 0 && state != 255) {
        return 0;
    }
    c->format = CFG_FORMAT;
    c->magic = 0x4f54;
    c->state = PENDING;
    c->record_crc = crc32((const uint8_t *)c + 4, 152);
    if (!cfg_valid(c)) {
        return 0;
    }
    /* Reject an unusable URL before any durable state change. Parse a copy:
     * the shared boot parser splits host/path in place. */
    char url[sizeof(c->url)];
    Url parsed;
    memcpy(url, c->url, sizeof(url));
    if (strlen(url) != c->url_len || !url_parse_impl(url, &parsed)) {
        return 0;
    }
    /* Numeric-only hosts must be valid dotted IPv4, not a failed DNS attempt. */
    const char *h = parsed.host;
    while ((*h >= '0' && *h <= '9') || *h == '.') {
        h++;
    }
    if (!*h) {
        h = parsed.host;
        for (uint8_t i = 0; i < 4; i++) {
            uint16_t value = 0;
            uint8_t digits = 0;
            while (*h >= '0' && *h <= '9') {
                value = value * 10 + (*h++ - '0');
                if (++digits > 3 || value > 255) {
                    return 0;
                }
            }
            if (!digits || *h != (i == 3 ? 0 : '.')) {
                return 0;
            }
            if (i != 3) {
                h++;
            }
        }
    }
    /* State ARMING first: any interrupted preparation fails closed.
     * Invalidate magic, fill payload, then commit magic and PENDING last. */
    ee_write(CFG_BASE + 3, 0x5a);
    ee_write(CFG_BASE, 0);
    ee_write(CFG_BASE + 1, 0);
    const uint8_t *p = (const uint8_t *)c;
    for (uint8_t i = 4; i < sizeof(Config); i++) {
        ee_write(CFG_BASE + i, p[i]);
    }
    ee_write(CFG_BASE + 2, CFG_FORMAT);
    ee_write(CFG_BASE, p[0]);
    ee_write(CFG_BASE + 1, p[1]);
    ee_write(CFG_BASE + 3, PENDING);
    return 1;
}
