/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "net.h"
uint8_t network_configure(void) {
    /* cfg was validated before OTA: one EEPROM record and one CRC. */
    if (cfg.network_mode != NETWORK_STATIC && dhcp()) {
        return 1;
    }
    if (cfg.network_mode == NETWORK_DHCP) {
        return 0;
    }
    net_close();
    net_config(cfg.ip, cfg.mask, cfg.gateway);
    memcpy(dns_server, cfg.dns, 4);
    return 1;
}
