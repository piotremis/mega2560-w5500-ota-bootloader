/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "boot.h"
Config cfg;
uint8_t cfg_valid(const Config *c) {
    if (c->magic != 0x4f54 || c->format != CFG_FORMAT || c->network_mode > NETWORK_STATIC ||
        crc32((const uint8_t *)c + 4, 152) != c->record_crc) {
        return 0;
    }
    uint8_t any = 0;
    for (uint8_t i = 0; i < 6; i++) {
        any |= c->mac[i];
    }
    if (!any || (c->mac[0] & 1)) {
        return 0;
    }
    /* Factory IDLE carries identity/network settings, but no image request. */
    if (c->state == 0 && !c->image_size && !c->url_len) {
        return 1;
    }
    return c->url_len >= 9 && c->url_len <= 100 && c->url[c->url_len] == 0 && c->image_size &&
           c->image_size <= APP_END;
}
uint8_t cfg_load(void) {
    uint8_t *p = (uint8_t *)&cfg;
    for (uint8_t i = 0; i < sizeof(Config); i++) {
        p[i] = ee_read(CFG_BASE + i);
    }
    return cfg_valid(&cfg);
}
void cfg_done(void) {
    ee_write(CFG_BASE + 3, 0);
    cfg.state = 0;
}
uint8_t cfg_bootable(uint8_t valid) {
    return cfg.state != PENDING && cfg.state != 0x5a && (!valid || cfg.state == 0);
}
