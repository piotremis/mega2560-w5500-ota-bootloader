/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef OTA_REQUEST_H
#define OTA_REQUEST_H
#include "../src/boot.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Fill image_size, image_crc, version, mac, url, url_len and network_mode.
 * For NETWORK_FALLBACK/NETWORK_STATIC fill ip, mask, gateway, dns too.
 * Preserve provisioned mac, serial_number and network fields (load cfg first).
 * Zero reserved fields. Entire 160-byte record is committed together.
 * Returns 1 only after durable commit. Refuses to replace a pending request.
 * Caller must then reset with watchdog. Does not decide version policy. */
uint8_t ota_request(Config *record);
#ifdef __cplusplus
}
#endif
#endif
