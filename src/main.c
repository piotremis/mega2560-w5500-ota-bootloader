/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "boot.h"
#include "net.h"
uint8_t packet[600], page[256];
int main(void) {
    platform_init();
    for (;;) {
        stk500(); /* Always offer UART recovery, also on watchdog reset. */
#if STAGE >= 8
        uint8_t valid = cfg_load();
        if (valid && cfg.state == PENDING) {
            if (ota()) {
                cfg_done();
            } else {
                net_close();
                error_led();
                continue;
            }
        }
        /* Missing metadata disables OTA. Pending/arming still blocks a partial image. */
        if (!cfg_bootable(valid)) {
            error_led();
            continue;
        }
#elif STAGE >= 4
        /* Intermediate integration builds exercise just the introduced stage. */
        cfg_load();
        if (net_init(cfg.mac)) {
#if STAGE >= 5
            if (dhcp()) {
#if STAGE >= 6
                Url u;
                uint8_t ip[4];
                if (url_parse(cfg.url, &u) && dns(u.host, ip)) {
#if STAGE >= 7
                    http_open(&u, ip, cfg.image_size);
#endif
                }
#endif
            }
#endif
        }
#endif
        if (flash_read(0) != 255 || flash_read(1) != 255) {
            application();
        }
    }
}
